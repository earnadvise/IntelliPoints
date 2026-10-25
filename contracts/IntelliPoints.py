# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *
import json

# Fixed amount of points awarded per accepted contribution claim.
MINT_AMOUNT: int = 100


class IntelliPoints(gl.Contract):
    """
    A permissionless points token on GenLayer.

    Anyone can:
      - mint(claim)    — earn MINT_AMOUNT points by submitting a contribution
                         claim that passes LLM consensus via the Equivalence Principle.
      - transfer(to, amount) — send points to another address.
      - burn(amount)   — destroy your own points.

    Invariant: sum(balances) == total_supply at all times.
    """

    balances: TreeMap[Address, u256]
    total_supply: u256

    def __init__(self) -> None:
        self.total_supply = u256(0)

    # ─── Read methods ────────────────────────────────────────────────────────

    @gl.public.view
    def balance_of(self, account: Address) -> u256:
        """Return the point balance of *account*."""
        return self.balances.get(account, u256(0))

    @gl.public.view
    def get_total_supply(self) -> u256:
        """Return the global total supply of points."""
        return self.total_supply

    # ─── Write methods ───────────────────────────────────────────────────────

    @gl.public.write
    def mint(self, claim: str) -> None:
        """
        Attempt to mint MINT_AMOUNT points to the caller.

        The claim is judged by an LLM using the Equivalence Principle with a
        custom validator function (run_nondet_unsafe). The leader and each
        validator independently prompt the LLM and compare the `approved`
        field of their results. If consensus agrees the claim is a genuine
        contribution, points are credited; otherwise the transaction is
        undetermined and no state is changed.
        """
        caller: Address = gl.message.sender_account

        # Build the prompt outside the non-deterministic block so the same
        # string reaches every node.
        prompt = f"""You are an impartial judge for a contribution-points system.
A participant is claiming credit for a contribution. Evaluate whether the
claim describes a genuine, meaningful contribution (writing code, fixing a
bug, writing documentation, reporting a real issue, creating useful content,
providing thoughtful feedback, etc.).

Claim: "{claim}"

Respond with ONLY valid JSON in this exact format, nothing else:
{{
  "approved": true,
  "reason": "brief one-sentence justification"
}}
or
{{
  "approved": false,
  "reason": "brief one-sentence justification"
}}
"""

        def _call_llm() -> dict:
            """Run the LLM and return a parsed dict with at least 'approved' (bool)."""
            raw = gl.nondet.exec_prompt(prompt)
            # Strip markdown code fences if the model adds them.
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("```")[1]
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:]
            result = json.loads(cleaned.strip())
            assert isinstance(result.get("approved"), bool), "approved must be bool"
            return result

        def leader_fn() -> dict:
            return _call_llm()

        def validator_fn(leader_result: gl.vm.Result) -> bool:
            # If the leader errored, reject.
            if not isinstance(leader_result, gl.vm.Return):
                return False

            leader_approved: bool = leader_result.calldata.get("approved", False)

            # Run our own independent judgment.
            try:
                validator_result = _call_llm()
            except Exception:
                # If we cannot produce a verdict, reject to be safe.
                return False

            validator_approved: bool = validator_result.get("approved", False)

            # Both must agree on the approval decision.
            return leader_approved == validator_approved

        # Run the non-deterministic block; raises if consensus is not reached.
        consensus_result: dict = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)

        approved: bool = consensus_result.get("approved", False)

        if approved:
            current_balance = self.balances.get(caller, u256(0))
            self.balances[caller] = current_balance + u256(MINT_AMOUNT)
            self.total_supply = self.total_supply + u256(MINT_AMOUNT)

    @gl.public.write
    def transfer(self, to: Address, amount: u256) -> None:
        """
        Transfer *amount* points from the caller to *to*.

        Reverts if:
          - amount is zero
          - caller and recipient are the same address
          - caller's balance is insufficient
        """
        caller: Address = gl.message.sender_account

        if amount == u256(0):
            raise gl.UserError("Transfer amount must be greater than zero")

        if caller == to:
            raise gl.UserError("Cannot transfer to yourself")

        sender_balance = self.balances.get(caller, u256(0))
        if sender_balance < amount:
            raise gl.UserError("Insufficient balance")

        self.balances[caller] = sender_balance - amount
        recipient_balance = self.balances.get(to, u256(0))
        self.balances[to] = recipient_balance + amount

    @gl.public.write
    def burn(self, amount: u256) -> None:
        """
        Destroy *amount* points from the caller's balance.

        Reverts if:
          - amount is zero
          - caller's balance is insufficient
        """
        caller: Address = gl.message.sender_account

        if amount == u256(0):
            raise gl.UserError("Burn amount must be greater than zero")

        sender_balance = self.balances.get(caller, u256(0))
        if sender_balance < amount:
            raise gl.UserError("Insufficient balance")

        self.balances[caller] = sender_balance - amount
        self.total_supply = self.total_supply - amount
