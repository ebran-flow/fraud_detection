"""
Provider Factory - Routes to correct models based on provider code
Follows factory pattern for DRY and maintainability
"""
from typing import Type, Tuple
from ..models.base import Base
from ..models.providers.uatl import UATLRawStatement, UATLProcessedStatement
from ..models.providers.umtn import UMTNRawStatement, UMTNProcessedStatement


class ProviderFactory:
    """Factory for getting provider-specific models and configuration"""

    # Provider registry
    PROVIDERS = {
        'UATL': {
            'name': 'Airtel Uganda',
            'raw_model': UATLRawStatement,
            'processed_model': UATLProcessedStatement,
            'balance_field': 'balance',           # UATL uses 'balance'
            'supports_commission': False,
        },
        'UMTN': {
            'name': 'MTN Uganda',
            'raw_model': UMTNRawStatement,
            'processed_model': UMTNProcessedStatement,
            'balance_field': 'float_balance',     # UMTN uses 'float_balance'
            'supports_commission': True,
        }
    }

    @classmethod
    def get_raw_model(cls, provider_code: str) -> Type[Base]:
        """
        Get raw statements model for provider

        Args:
            provider_code: Provider code ('UATL', 'UMTN', etc.)

        Returns:
            SQLAlchemy model class

        Raises:
            ValueError: If provider not supported
        """
        if provider_code not in cls.PROVIDERS:
            raise ValueError(f"Unknown provider: {provider_code}. Supported: {list(cls.PROVIDERS.keys())}")
        return cls.PROVIDERS[provider_code]['raw_model']

    @classmethod
    def get_processed_model(cls, provider_code: str) -> Type[Base]:
        """
        Get processed statements model for provider

        Args:
            provider_code: Provider code ('UATL', 'UMTN', etc.)

        Returns:
            SQLAlchemy model class

        Raises:
            ValueError: If provider not supported
        """
        if provider_code not in cls.PROVIDERS:
            raise ValueError(f"Unknown provider: {provider_code}. Supported: {list(cls.PROVIDERS.keys())}")
        return cls.PROVIDERS[provider_code]['processed_model']

    @classmethod
    def get_models(cls, provider_code: str) -> Tuple[Type[Base], Type[Base]]:
        """
        Get both raw and processed models for provider

        Args:
            provider_code: Provider code

        Returns:
            Tuple of (RawModel, ProcessedModel)
        """
        return (cls.get_raw_model(provider_code), cls.get_processed_model(provider_code))

    @classmethod
    def get_balance_field(cls, provider_code: str) -> str:
        """
        Get the balance field name for provider

        UATL uses 'balance'
        UMTN uses 'float_balance'

        Args:
            provider_code: Provider code

        Returns:
            Balance field name
        """
        if provider_code not in cls.PROVIDERS:
            raise ValueError(f"Unknown provider: {provider_code}")
        return cls.PROVIDERS[provider_code]['balance_field']

    @classmethod
    def supports_commission(cls, provider_code: str) -> bool:
        """Check if provider supports commission tracking"""
        if provider_code not in cls.PROVIDERS:
            return False
        return cls.PROVIDERS[provider_code]['supports_commission']

    @classmethod
    def is_supported(cls, provider_code: str) -> bool:
        """Check if provider is supported"""
        return provider_code in cls.PROVIDERS

    @classmethod
    def get_all_providers(cls) -> list:
        """Get list of all supported provider codes"""
        return list(cls.PROVIDERS.keys())

    @classmethod
    def get_provider_name(cls, provider_code: str) -> str:
        """Get human-readable provider name"""
        if provider_code not in cls.PROVIDERS:
            return provider_code
        return cls.PROVIDERS[provider_code]['name']


# Convenience function for common use case
def get_provider_models(provider_code: str):
    """
    Convenience function to get both models

    Usage:
        RawModel, ProcessedModel = get_provider_models('UATL')
    """
    return ProviderFactory.get_models(provider_code)
