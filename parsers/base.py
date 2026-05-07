from abc import ABC, abstractmethod


class BankParser(ABC):
    @abstractmethod
    def parse(self, pdf_path: str) -> list[dict]:
        """Return a list of transaction dicts with keys:
        date, time, name, bank, notes, transaction_type,
        transaction_id, category, amount, amount_raw
        """
