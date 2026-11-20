from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, TypedDict, Union


TfaMethod = Literal["AUTHENTICATOR", "EMAIL", "SMS", "MAGIC_LINK"]

VaultFieldType = Literal[
    "Text",
    "Email",
    "Url",
    "Phone",
    "Date",
    "MonthYear",
    "Address",
    "Concealed",
    "Totp",
]


class VaultAddress(TypedDict):
    street: str
    city: str
    state: str
    zip: str
    country: str


@dataclass
class VaultAdditionalField:
    """A named, typed value on a vault entry.

    ``value`` is a :class:`VaultAddress` dict only for ``Address``. Workflows
    read it as ``{{context.inputs.<ALIAS>.FIELDS.<name>}}``.
    """

    name: str
    type: VaultFieldType
    value: Union[str, VaultAddress]


@dataclass
class VaultAdditionalFieldWarning:
    """An additional field of the bound secret provider item that was skipped."""

    name: str
    reason: str


@dataclass
class VaultSecurityQuestion:
    """A security question and its answer, answered by a
    ``SECURITY_QUESTION`` TFA node."""

    question: str
    answer: str


@dataclass
class VaultSecurityQuestionWarning:
    """A security question of the bound secret provider item that was skipped."""

    question: str
    reason: str


@dataclass
class ProxyConfig:
    enable: bool
    target_ip: Optional[str] = None


@dataclass
class VaultEntryInput:
    """Fields a client can set when creating or updating a vault entry.

    ``tfa_methods`` replaces the deprecated ``tfa_method``. The API ignores
    ``tfa_method`` when ``tfa_methods`` is set; on its own it replaces the
    stored methods with that single method.
    ``additional_fields`` and ``security_questions`` replace the stored lists.

    Omits server-managed fields (``id``, ``created_at``, ``workspace_id``,
    ``organization_id``, ``site_identifier``, ``session_data_set_at``,
    ``effective_expires_at``) and server-computed reflections
    (``tfa_email``, ``tfa_phone_number``). Those only appear on
    :class:`VaultEntry` responses.

    ``permissioned_user_id`` is required. ``domain`` is optional: an entry
    without a domain is addressed by its user ID alone, and the SDK leaves
    ``domain`` out of the request when it is ``None``. Without a ``domain``, an
    update uses the only entry of that user ID and the API answers 409 (listing
    the domains) when the user ID has several.

    Settings left as ``None`` are not sent, so the entry inherits the value
    from its domain's settings (see ``client.vault.update_site_settings``).
    Two values mean "turned off although the domain sets a value":
    ``max_concurrency=-1`` (no concurrency limit) and a zero interval such as
    ``"0 seconds"`` for ``expiry_time_from_last_use`` and
    ``expiry_time_from_session_data_set`` (no expiry).
    """

    domain: Optional[str] = None
    permissioned_user_id: str = None  # type: ignore[assignment]
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    password: Optional[str] = None
    secret_provider_id: Optional[str] = None
    secret_ref: Optional[str] = None
    secret_cache_ttl_seconds: Optional[int] = None
    tfa_secret: Optional[str] = None
    tfa_method: Optional[TfaMethod] = None
    user_agent: Optional[str] = None
    user_alias: Optional[str] = None
    location: Optional[str] = None
    ip_address: Optional[str] = None
    session_id: Optional[str] = None
    allow_multiple_sessions: Optional[bool] = None
    max_concurrency: Optional[int] = None
    prevent_concurrency_during_login: Optional[bool] = None
    cookies: Optional[Any] = None
    local_storage: Optional[Any] = None
    session_storage: Optional[Any] = None
    persist_cookies: Optional[bool] = None
    persist_local_storage: Optional[bool] = None
    persist_session_storage: Optional[bool] = None
    cookie_domain_to_store: Optional[str] = None
    skip_csrf_cookies: Optional[bool] = None
    proxy: Optional[ProxyConfig | dict[str, Any]] = None
    proxy_string: Optional[str] = None
    proxy_setting: Optional[Literal["random", "static", "country", "custom"]] = None
    proxy_value: Optional[str] = None
    expiry_time_from_last_use: Optional[str] = None
    expiry_time_from_session_data_set: Optional[str] = None
    tfa_methods: Optional[List[TfaMethod]] = None
    additional_fields: Optional[List[VaultAdditionalField]] = None
    security_questions: Optional[List[VaultSecurityQuestion]] = None

    def __post_init__(self) -> None:
        if self.permissioned_user_id is None:
            raise TypeError(
                "VaultEntryInput() missing required argument: 'permissioned_user_id'"
            )


@dataclass
class VaultEntry:
    """Full shape of a vault entry as returned by the API.

    Includes all writable fields plus server-managed fields
    (``id``, ``workspace_id``, ``organization_id``, ``site_identifier``,
    ``created_at``) and server-computed reflections
    (``tfa_email``, ``tfa_phone_number``, ``session_data_set_at``,
    ``effective_expires_at``). Setting any of the latter on create/update
    requests has no effect; the server ignores them.

    ``tfa_method`` is deprecated and reads as the first of ``tfa_methods``.

    ``domain`` is ``None`` for an entry without a domain.

    ``max_concurrency``, ``expiry_time_from_last_use`` and
    ``expiry_time_from_session_data_set`` are the entry's own values; ``None``
    means the entry inherits the domain's setting. ``max_concurrency=-1`` or a
    zero interval (``"0 seconds"``) means the entry turns the limit off although
    the domain sets a value.
    """

    domain: Optional[str]
    permissioned_user_id: str
    id: Optional[str] = None
    workspace_id: Optional[str] = None
    organization_id: Optional[str] = None
    site_identifier: Optional[str] = None
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    password: Optional[str] = None
    secret_provider_id: Optional[str] = None
    secret_ref: Optional[str] = None
    secret_cache_ttl_seconds: Optional[int] = None
    tfa_secret: Optional[str] = None
    tfa_method: Optional[TfaMethod] = None
    tfa_email: Optional[str] = None
    tfa_phone_number: Optional[str] = None
    user_agent: Optional[str] = None
    user_alias: Optional[str] = None
    location: Optional[str] = None
    ip_address: Optional[str] = None
    session_id: Optional[str] = None
    allow_multiple_sessions: Optional[bool] = None
    max_concurrency: Optional[int] = None
    prevent_concurrency_during_login: Optional[bool] = None
    cookies: Optional[Any] = None
    local_storage: Optional[Any] = None
    session_storage: Optional[Any] = None
    persist_cookies: Optional[bool] = None
    persist_local_storage: Optional[bool] = None
    persist_session_storage: Optional[bool] = None
    cookie_domain_to_store: Optional[str] = None
    skip_csrf_cookies: Optional[bool] = None
    proxy: Optional[ProxyConfig] = None
    proxy_string: Optional[str] = None
    proxy_setting: Optional[Literal["random", "static", "country", "custom"]] = None
    proxy_value: Optional[str] = None
    expiry_time_from_last_use: Optional[str] = None
    expiry_time_from_session_data_set: Optional[str] = None
    session_data_set_at: Optional[str] = None
    effective_expires_at: Optional[str] = None
    created_at: Optional[str] = None
    tfa_methods: Optional[List[TfaMethod]] = None
    additional_fields: Optional[List[VaultAdditionalField]] = None
    additional_field_warnings: Optional[List[VaultAdditionalFieldWarning]] = None
    security_questions: Optional[List[VaultSecurityQuestion]] = None
    security_question_warnings: Optional[List[VaultSecurityQuestionWarning]] = None


@dataclass
class GetVaultEntriesFilters:
    permissioned_user_id: Optional[str] = None
    domain: Optional[str] = None
    decryptCredentials: Optional[bool] = None


@dataclass
class VaultTfaCode:
    """The current 2FA code for a vault entry.

    ``expires_in_seconds`` is set for authenticator (TOTP) codes; ``received_at``
    is set for email codes.
    """

    type: str  # "authenticator" | "email"
    code: str
    expires_in_seconds: Optional[int] = None
    received_at: Optional[str] = None

    def __repr__(self) -> str:
        # Redact the code so debug/log output of the object never leaks a live
        # OTP. The value is still accessible via the ``code`` attribute.
        return (
            "VaultTfaCode("
            f"type={self.type!r}, "
            "code='<redacted>', "
            f"expires_in_seconds={self.expires_in_seconds!r}, "
            f"received_at={self.received_at!r})"
        )


SiteSettingsKey = Literal[
    "max_concurrency",
    "allow_multiple_sessions",
    "prevent_concurrency_during_login",
    "expiry_time_from_last_use",
    "expiry_time_from_session_data_set",
    "persist_cookies",
    "persist_local_storage",
    "persist_session_storage",
    "skip_csrf_cookies",
    "cookie_domain_to_store",
    "login_workflow_id",
]


@dataclass
class SiteSettingsValues:
    """The defaults a domain sets. ``None`` means the domain sets nothing for
    that setting and the platform default applies."""

    allow_multiple_sessions: Optional[bool] = None
    cookie_domain_to_store: Optional[str] = None
    expiry_time_from_last_use: Optional[str] = None
    expiry_time_from_session_data_set: Optional[str] = None
    login_workflow_id: Optional[str] = None
    max_concurrency: Optional[int] = None
    persist_cookies: Optional[bool] = None
    persist_local_storage: Optional[bool] = None
    persist_session_storage: Optional[bool] = None
    prevent_concurrency_during_login: Optional[bool] = None
    skip_csrf_cookies: Optional[bool] = None


@dataclass
class SiteSettings:
    """The settings of one domain in the workspace: the defaults every vault
    entry on the domain inherits unless it sets its own value.

    ``entry_count`` is the number of entries in the workspace on the domain.
    ``overrides`` maps each setting to how many of those entries set their own
    value instead of inheriting the default.
    """

    id: str
    domain: str
    settings: SiteSettingsValues
    entry_count: int
    overrides: Dict[str, int] = field(default_factory=dict)


@dataclass
class SiteSettingsEntry:
    """A vault entry on a domain.

    ``overridden`` lists the settings the entry sets itself. Every other
    setting is read from the domain defaults.
    """

    id: str
    permissioned_user_id: str
    overridden: List[str] = field(default_factory=list)


@dataclass
class SiteSettingsEntryOverrides:
    """The settings one vault entry sets itself (``overridden``). Every other
    setting is read from the domain settings. ``domain`` is ``None`` for an
    entry without a domain."""

    id: str
    domain: Optional[str]
    overridden: List[str] = field(default_factory=list)
