const String _apiBaseUrl = String.fromEnvironment('API_BASE_URL');
const String _chatbotBaseUrl = String.fromEnvironment('CHATBOT_BASE_URL');

Uri apiUri(String path) => _configuredUri(_apiBaseUrl, 'API_BASE_URL', path);

Uri chatbotUri(String path) =>
    _configuredUri(_chatbotBaseUrl, 'CHATBOT_BASE_URL', path);

Uri _configuredUri(String baseUrl, String defineName, String path) {
  if (baseUrl.isEmpty) {
    throw StateError(
      '$defineName is not configured. See dart_defines.example.json.',
    );
  }

  final normalizedBaseUrl = baseUrl.endsWith('/')
      ? baseUrl.substring(0, baseUrl.length - 1)
      : baseUrl;
  return Uri.parse('$normalizedBaseUrl/$path');
}
