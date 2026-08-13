"""Custom exception hierarchy for gitplus."""


class GitPlusError(Exception):
    """Base class for all business exceptions."""


class GitRepositoryError(GitPlusError):
    """Raised when Git repository metadata cannot be resolved."""


class GitCommandError(GitPlusError):
    """Raised when a Git command fails."""


class GitCommandTimeoutError(GitCommandError):
    """Raised when a Git command exceeds its timeout."""


class GitParseError(GitPlusError):
    """Raised when Git output cannot be parsed."""


class ConfigurationError(GitPlusError):
    """Raised when configuration is invalid."""


class SecurityError(GitPlusError):
    """Base class for security-related errors."""


class SecurityConfigurationError(SecurityError):
    """Raised when security configuration is invalid."""


class SecurityScanError(SecurityError):
    """Raised when sensitive content scanning fails."""


class SensitiveContentError(SecurityError):
    """Raised when unsafe sensitive content is detected."""


class MaskingError(SecurityError):
    """Raised when masking sensitive content fails."""


class LLMProviderError(GitPlusError):
    """Raised when an LLM provider call fails."""


class LLMResponseError(GitPlusError):
    """Raised when an LLM response cannot be parsed or validated."""


class AIError(GitPlusError):
    """Base class for AI-related errors."""


class AIConfigurationError(AIError):
    """Raised when AI configuration is invalid."""


class AIProviderError(AIError):
    """Raised when an AI provider call fails."""


class AIAuthenticationError(AIProviderError):
    """Raised when AI authentication fails."""


class AIRateLimitError(AIProviderError):
    """Raised when an AI provider rate limits requests."""


class AITimeoutError(AIProviderError):
    """Raised when an AI provider times out."""


class AIResponseError(AIError):
    """Raised when an AI response cannot be parsed."""


class AIResponseValidationError(AIResponseError):
    """Raised when an AI response fails schema validation."""


class PromptTemplateError(AIError):
    """Raised when a prompt template cannot be rendered."""


class CommitGenerationError(AIError):
    """Raised when commit message generation fails."""


class TopicDetectionError(AIError):
    """Raised when topic detection fails."""


class DatabaseError(GitPlusError):
    """Raised when persistence fails."""


class StorageError(GitPlusError):
    """Base class for storage-related errors."""


class DatabaseInitializationError(StorageError):
    """Raised when database initialization fails."""


class DatabaseConnectionError(StorageError):
    """Raised when database connection fails."""


class DatabaseMigrationError(StorageError):
    """Raised when database migration fails."""


class RepositoryOperationError(StorageError):
    """Raised when a repository operation fails."""


class RecordNotFoundError(StorageError):
    """Raised when a requested record does not exist."""


class DuplicateRecordError(StorageError):
    """Raised when a duplicate record is detected."""


class DataSerializationError(StorageError):
    """Raised when JSON field serialization fails."""


class WorklogValidationError(GitPlusError):
    """Raised when worklog input is invalid."""


class WeeklyError(GitPlusError):
    """Base class for weekly report errors."""


class WeeklyConfigurationError(WeeklyError):
    """Raised when weekly configuration is invalid."""


class WeeklyDateRangeError(WeeklyError):
    """Raised when weekly date range is invalid."""


class WeeklyCollectionError(WeeklyError):
    """Raised when weekly data collection fails."""


class WeeklyGenerationError(WeeklyError):
    """Raised when weekly generation fails."""


class WeeklyValidationError(WeeklyError):
    """Raised when weekly validation fails."""


class WeeklyConfirmationError(WeeklyError):
    """Raised when weekly confirmation fails."""


class WeeklyExportError(WeeklyError):
    """Raised when weekly export fails."""


class WeeklySourceError(WeeklyError):
    """Raised when weekly source validation fails."""


class EmptyWeeklyDataError(WeeklyError):
    """Raised when no weekly data is available."""


class ReportGenerationError(GitPlusError):
    """Raised when report generation fails."""


class NotificationError(GitPlusError):
    """Base class for notification errors."""


class NotificationConfigurationError(NotificationError):
    """Raised when notification configuration is invalid."""


class NotificationValidationError(NotificationError):
    """Raised when a report is not eligible for notification."""


class NotificationConfirmationError(NotificationError):
    """Raised when a user does not confirm notification sending."""


class DuplicateNotificationError(NotificationError):
    """Raised when duplicate notification protection blocks sending."""


class NotificationContentTooLargeError(NotificationError):
    """Raised when a notification payload exceeds configured limits."""


class NotificationSecurityError(NotificationError):
    """Raised when notification content contains blocking sensitive data."""


class FeishuError(NotificationError):
    """Base class for Feishu notification errors."""


class FeishuConnectionError(FeishuError):
    """Raised when Feishu cannot be reached."""


class FeishuTimeoutError(FeishuError):
    """Raised when a Feishu request times out."""


class FeishuRateLimitError(FeishuError):
    """Raised when Feishu rate limits requests."""


class FeishuAuthenticationError(FeishuError):
    """Raised when Feishu rejects application credentials."""


class FeishuRequestError(FeishuError):
    """Raised when Feishu rejects the request payload."""


class FeishuResponseError(FeishuError):
    """Raised when a Feishu response cannot be parsed."""
