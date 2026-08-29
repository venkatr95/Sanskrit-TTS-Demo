import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:just_audio/just_audio.dart';

import '../models/timed_text.dart';

class TtsService {
  static const String apiBase = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://localhost:8000',
  );

  final AudioPlayer player = AudioPlayer();

  Stream<Duration> get positionStream => player.positionStream;

  Future<TtsResult> generate({
    required String text,
    required String style,
    required double speed,
    required int pauseMs,
  }) async {
    final response = await http.post(
      Uri.parse('$apiBase/generate'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'text': text,
        'style': style,
        'speed': speed,
        'pause_ms': pauseMs,
        'alignment': 'word',
      }),
    );

    if (response.statusCode != 200) {
      throw Exception(
        'TTS server error ${response.statusCode}: ${response.body}',
      );
    }

    return TtsResult.fromJson(
      jsonDecode(response.body) as Map<String, dynamic>,
    );
  }

  Future<void> loadAndPlay(String relativeUrl) async {
    final url = relativeUrl.startsWith('http')
        ? relativeUrl
        : '$apiBase$relativeUrl';

    await player.setUrl(url);
    await player.play();
  }

  Future<void> dispose() async {
    await player.dispose();
  }
}
