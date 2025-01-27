import logging
import nordigen_account

_LOGGER = logging.getLogger(__name__)

class NordigenWrapper:
    """A small wrapper around BankAccountManager to fetch data with updated tokens if needed."""

    def __init__(self, secret_id, secret_key, requisition_id, refresh_token=None):
        """
        Initialize a NordigenWrapper object.

        Args:
            secret_id (str): Nordigen API secret ID.
            secret_key (str): Nordigen API secret key.
            requisition_id (str): Requisition ID to fetch linked account IDs
            refresh_token (str, optional): Refresh token to obtain the access token.

        """

        self._secret_id = secret_id
        self._secret_key = secret_key
        self._requisition_id = requisition_id
        self._refresh_token = refresh_token

        self.client = None
        self.manager = None
        self.accounts = []

        self._initialize_manager()

    def _initialize_manager(self):
        """Create the NordigenClient, fetch new token if needed, and create BankAccountManager."""
        # create_nordigen_client attempts to use refresh_token if provided,
        # otherwise fetches a new one
        try:
            client, new_refresh_token = nordigen_account.create_nordigen_client(
                secret_id=self._secret_id,
                secret_key=self._secret_key,
                refresh_token=self._refresh_token
            )
            self.client = client
            if new_refresh_token:
                self._refresh_token = new_refresh_token  # store updated token

            # Instantiate BankAccountManager with fetch_data=False initially,
            # returns only bank account IDs
            self.manager = nordigen_account.BankAccountManager(
                client=self.client, requisition_id=self._requisition_id, fetch_data=False
            )

            self.accounts = self.manager.accounts

        except RuntimeError as e:
            _LOGGER.error("Failed to initialize Nordigen manager: %s", str(e))

    def update_all_accounts(self):
        """
        Called by the DataUpdateCoordinator to refresh each account's data.
        Re-initialize itself if the token or requisition ID changed.
        """
        if not self.manager:
            self._initialize_manager()

        # Refresh account and balance data for each existing BankAccount
        for acc in self.manager.accounts:
            acc.update_account_data()
            acc.update_balance_data()

    @property
    def refresh_token(self):
        return self._refresh_token

    @property
    def requisition_id(self):
        return self._requisition_id

    @requisition_id.setter
    def requisition_id(self, new_id):
        self._requisition_id = new_id
        # re-initialize if requisition ID changed
        self._initialize_manager()
