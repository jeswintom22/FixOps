from app.services.ai import AIServiceStub, AzureOpenAIService, ProviderAIService

AzureAIService = ProviderAIService
AzureAIServiceStub = AIServiceStub

__all__ = ["AzureAIService", "AzureAIServiceStub", "AzureOpenAIService"]
