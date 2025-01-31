from nordigen_account import create_nordigen_client, BankAccountManager, NordigenAPIError

class NordigenWrapper:
    """A small wrapper around BankAccountManager to fetch data with updated tokens if needed."""

    def __init__(self, secret_id, secret_key, requisition_id, refresh_token=None):
        self._secret_id = secret_id
        self._secret_key = secret_key
        self._requisition_id = requisition_id
        self._refresh_token = refresh_token

        self.client = None
        self.manager = None
        self.accounts = []

        self._initialize_manager()

    def _initialize_manager(self):
        try:
            client, new_refresh_token = create_nordigen_client(
                secret_id=self._secret_id,
                secret_key=self._secret_key,
                refresh_token=self._refresh_token
            )
            self.client = client
            if new_refresh_token:
                self._refresh_token = new_refresh_token

            self.manager = BankAccountManager(
                client=self.client, requisition_id=self._requisition_id, fetch_data=False
            )
            self.accounts = self.manager.accounts

        except NordigenAPIError as e:
            raise
        except RuntimeError as e:
            raise

    def update_all_accounts(self):
        if not self.manager:
            self._initialize_manager()

        try:
            for acc in self.manager.accounts:
                acc.update_account_data()
                acc.update_balance_data()
        except NordigenAPIError as e:
            raise

    @property
    def refresh_token(self):
        return self._refresh_token

    @property
    def requisition_id(self):
        return self._requisition_id

    @requisition_id.setter
    def requisition_id(self, new_id):
        self._requisition_id = new_id
        self._initialize_manager()
