# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *
import json

# Fixed points awarded per accepted contribution
MINT_AMOUNT: int = 100


class IntelliPoints(gl.Contract):
    """
    Permissionless contribution-points token on GenLayer.

    To mint points, a caller must supply:
      - A short description of their contribution
      - A public evidence URL (GitHub PR, issue, commit, merged diff, etc.)

    During mint, each node independently fetches the evidence URL and asks
    the LLM to judge whether the page confirms a genuine contribution.
    Leader and validator must agree (run_nondet_unsafe) before any points
    are credited. Free-text claims with no verifiable evidence are rejected.

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
    def mint(self, description: str, evidence_url: str) -> None:
        """
        Attempt to mint MINT_AMOUNT points to the caller.

        Parameters:
          description  — short plain-text summary of the contribution
                         (e.g. "Fixed null pointer bug in auth module")
          evidence_url — publicly accessible URL that contains verifiable
                         evidence of the contribution, such as:
                           - A GitHub pull request URL
                           - A GitHub issue URL
                           - A GitHub commit URL
                           - A merged diff page

        Each node independently fetches evidence_url, reads the live page
        content, and asks the LLM whether the page confirms the described
        contribution. Leader and validator compare their `approved` fields
        via run_nondet_unsafe — both must agree before points are minted.
        """
        if not description.strip():
            raise Exception("Description must not be empty")
        if not evidence_url.strip():
            raise Exception("evidence_url must not be empty")

        caller: Address = gl.message.sender_address

        def _fetch_and_judge() -> dict:
            """
            Fetch live evidence and ask the LLM to judge the contribution.
            Called independently on leader and each validator node.
            """
            response = gl.nondet.web.get(evidence_url)
            page_text = response.body.decode("utf-8")
            snippet = page_text[:4000] if len(page_text) > 4000 else page_text

            prompt = f"""You are an impartial judge for a contribution-points system.

A participant claims they made the following contribution:
"{description}"

They provided this evidence URL: {evidence_url}

Below is the LIVE content fetched from that URL:
--- EVIDENCE START ---
{snippet}
--- EVIDENCE END ---

Based ONLY on the evidence above (not prior knowledge), decide:
  - Does the fetched page confirm a genuine, meaningful contribution?
  - A genuine contribution includes: merged pull requests, closed issues with
    a fix, commits with substantive code changes, documented bug reports,
    or meaningful documentation updates.
  - Reject if: the page is unrelated, the PR/issue is still open with no
    meaningful activity, the change is trivial (typo, single character), or
    the evidence does not match the description.

Respond with ONLY valid JSON in exactly this format, nothing else:
{{
  "approved": true,
  "reason": "one sentence citing specific evidence from the page"
}}
or
{{
  "approved": false,
  "reason": "one sentence explaining what was missing or mismatched"
}}
"""
            raw = gl.nondet.exec_prompt(prompt)
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("```")[1]
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:]
            result = json.loads(cleaned.strip())
            assert isinstance(result.get("approved"), bool), "approved must be bool"
            return result

        def leader_fn() -> dict:
            return _fetch_and_judge()

        def validator_fn(leader_result: gl.vm.Result) -> bool:
            if not isinstance(leader_result, gl.vm.Return):
                return False
            leader_approved: bool = leader_result.calldata.get("approved", False)
            try:
                # Validator independently fetches the same URL and judges
                validator_result = _fetch_and_judge()
            except Exception:
                return False
            validator_approved: bool = validator_result.get("approved", False)
            # Both independent verdicts must agree
            return leader_approved == validator_approved

        consensus_result: dict = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
        approved: bool = consensus_result.get("approved", False)

        if approved:
            current_balance = self.balances.get(caller, u256(0))
            self.balances[caller] = current_balance + u256(MINT_AMOUNT)
            self.total_supply = self.total_supply + u256(MINT_AMOUNT)

    @gl.public.write
    def transfer(self, to: Address, amount: u256) -> None:
        """
        Transfer *amount* points from caller to *to*.

        Reverts if amount is zero, sender == recipient, or balance insufficient.
        """
        caller: Address = gl.message.sender_address
        if amount == u256(0):
            raise Exception("Transfer amount must be greater than zero")
        if caller == to:
            raise Exception("Cannot transfer to yourself")
        sender_balance = self.balances.get(caller, u256(0))
        if sender_balance < amount:
            raise Exception("Insufficient balance")
        self.balances[caller] = sender_balance - amount
        recipient_balance = self.balances.get(to, u256(0))
        self.balances[to] = recipient_balance + amount

    @gl.public.write
    def burn(self, amount: u256) -> None:
        """
        Destroy *amount* points from caller's balance.

        Reverts if amount is zero or balance insufficient.
        """
        caller: Address = gl.message.sender_address
        if amount == u256(0):
            raise Exception("Burn amount must be greater than zero")
        sender_balance = self.balances.get(caller, u256(0))
        if sender_balance < amount:
            raise Exception("Insufficient balance")
        self.balances[caller] = sender_balance - amount
        self.total_supply = self.total_supply - amount
