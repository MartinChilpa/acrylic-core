from django.utils import translation
from account.models import resolve_account_language


class AccountLanguageMiddleware:
	"""
	For authenticated requests, pin the language to the account's stored preference
	instead of relying on the browser's Accept-Language header.

	Runs after AuthenticationMiddleware and LocaleMiddleware, so request.user is
	populated and a default language is already active (from LocaleMiddleware).
	"""
	def __init__(self, get_response):
		self.get_response = get_response

	def __call__(self, request):
		if request.user.is_authenticated:
			try:
				account_language = resolve_account_language(request.user.account)
				translation.activate(account_language)
				request.LANGUAGE_CODE = account_language
			except Exception:
				pass

		response = self.get_response(request)
		return response
