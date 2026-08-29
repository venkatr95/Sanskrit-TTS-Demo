import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:async';

import 'models/timed_text.dart';
import 'services/tts_service.dart';
import 'widgets/karaoke_text.dart';
import 'widgets/player_bar.dart';

void main() {
  runApp(const SanskritKaraokeApp());
}

class SanskritKaraokeApp extends StatelessWidget {
  const SanskritKaraokeApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Sanskrit Karaoke TTS',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        brightness: Brightness.dark,
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF1DB954), // Spotify Green
          brightness: Brightness.dark,
        ),
        useMaterial3: true,
        scaffoldBackgroundColor: Colors.transparent,
      ),
      home: Scaffold(
        body: Container(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: [
                Color(0xFF2B2B2B),
                Color(0xFF121212),
              ],
            ),
          ),
          child: SanskritReaderPage(),
        ),
      ),
    );
  }
}

class SanskritReaderPage extends StatefulWidget {
  const SanskritReaderPage({super.key});

  @override
  State<SanskritReaderPage> createState() => _SanskritReaderPageState();
}

class _SanskritReaderPageState extends State<SanskritReaderPage> {
  final _textController = TextEditingController(
    text: '''जातः कंसवधार्थाय भूभारोत्तरणाय च।
कौरवाणां विनाशाय दैत्यानां निधनाय च॥
पाण्डवानां हितार्थाय धर्मसंस्थापनाय च।
गृहाणार्घ्यं मया दत्तं देवक्या सहितो हरे॥''',
  );

  final _tts = TtsService();

  List<TimedSegment> _segments = [];
  String? _audioUrl;
  String _style = 'vedic';
  double _speed = 1.0;
  int _pauseMs = 90;

  bool _loading = false;
  double _progress = 0.0;
  Timer? _progressTimer;
  String? _error;

  @override
  void dispose() {
    _textController.dispose();
    _tts.dispose();
    super.dispose();
  }

  Future<void> _generate() async {
    FocusManager.instance.primaryFocus?.unfocus();

    final text = _textController.text.trim();
    if (text.isEmpty) {
      setState(() => _error = 'Enter Sanskrit text first.');
      return;
    }

    _progressTimer?.cancel();
    setState(() {
      _loading = true;
      _progress = 0.0;
      _error = null;
      _segments = [];
      _audioUrl = null;
    });

    _progressTimer = Timer.periodic(const Duration(milliseconds: 100), (timer) {
      if (!mounted) return;
      setState(() {
        _progress = _progress + (0.95 - _progress) * 0.02;
      });
    });

    try {
      final result = await _tts.generate(
        text: text,
        style: _style,
        speed: _speed,
        pauseMs: _pauseMs,
      );

      _progressTimer?.cancel();
      if (mounted) {
        setState(() => _progress = 1.0);
      }
      
      await Future.delayed(const Duration(milliseconds: 200));

      if (mounted) {
        setState(() {
          _segments = result.segments;
          _audioUrl = result.audioUrl;
        });
      }

      await _tts.loadAndPlay(result.audioUrl);
    } catch (e) {
      _progressTimer?.cancel();
      setState(() => _error = e.toString());
    } finally {
      if (mounted) {
        setState(() => _loading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.transparent,
      appBar: AppBar(
        title: const Text(
          'Sanskrit Karaoke',
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
        centerTitle: false,
        backgroundColor: Colors.transparent,
        elevation: 0,
      ),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1000),
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              children: [
                Expanded(
                  child: Container(
                    padding: const EdgeInsets.all(24),
                    child: Column(
                        children: [
                          Row(
                            children: [
                              Text(
                                'Sanskrit Reader',
                                style: Theme.of(context)
                                    .textTheme
                                    .headlineSmall,
                              ),
                              const Spacer(),
                              DropdownButton<String>(
                                value: _style,
                                items: const [
                                  DropdownMenuItem(
                                    value: 'reading',
                                    child: Text('📖 Reading'),
                                  ),
                                  DropdownMenuItem(
                                    value: 'chant',
                                    child: Text('🕉️ Chant'),
                                  ),
                                  DropdownMenuItem(
                                    value: 'vedic',
                                    child: Text('🔱 Vedic'),
                                  ),
                                  DropdownMenuItem(
                                    value: 'meditation',
                                    child: Text('🧘 Meditation'),
                                  ),
                                ],
                                onChanged: (v) {
                                  if (v != null) {
                                    setState(() => _style = v);
                                  }
                                },
                              ),
                            ],
                          ),
                          const SizedBox(height: 16),
                          Expanded(
                            child: _segments.isEmpty
                                ? TextField(
                                    controller: _textController,
                                    maxLines: null,
                                    expands: true,
                                    textAlignVertical: TextAlignVertical.top,
                                    style: const TextStyle(
                                      fontSize: 27,
                                      height: 1.8,
                                    ),
                                    decoration: const InputDecoration(
                                      hintText:
                                          'Paste Sanskrit text here...',
                                      border: OutlineInputBorder(),
                                    ),
                                  )
                                : KaraokeText(
                                    segments: _segments,
                                    positionStream: _tts.positionStream,
                                  ),
                          ),
                          if (_error != null) ...[
                            const SizedBox(height: 12),
                            Align(
                              alignment: Alignment.centerLeft,
                              child: Text(
                                _error!,
                                style: TextStyle(
                                  color: Theme.of(context)
                                      .colorScheme
                                      .error,
                                ),
                              ),
                            ),
                          ],
                        ],
                      ),
                    ),
                  ),
                const SizedBox(height: 16),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 18,
                    vertical: 12,
                  ),
                  decoration: BoxDecoration(
                    color: Colors.black.withOpacity(0.3),
                    borderRadius: BorderRadius.circular(16),
                  ),
                  child: Column(
                      children: [
                        Row(
                          children: [
                            const Text('Speed'),
                            Expanded(
                              child: Slider(
                                value: _speed,
                                min: 0.6,
                                max: 1.4,
                                divisions: 8,
                                label: '${_speed.toStringAsFixed(2)}×',
                                onChanged: (v) =>
                                    setState(() => _speed = v),
                              ),
                            ),
                            Text('${_speed.toStringAsFixed(2)}×'),
                          ],
                        ),
                        Row(
                          children: [
                            const Text('Pause'),
                            Expanded(
                              child: Slider(
                                value: _pauseMs.toDouble(),
                                min: 0,
                                max: 300,
                                divisions: 30,
                                label: '$_pauseMs ms',
                                onChanged: (v) =>
                                    setState(() => _pauseMs = v.round()),
                              ),
                            ),
                            Text('$_pauseMs ms'),
                          ],
                        ),
                        PlayerBar(
                          player: _tts.player,
                          loading: _loading,
                          hasAudio: _audioUrl != null,
                          onGenerate: _generate,
                        ),
                        if (_loading) ...[
                          const SizedBox(height: 16),
                          ClipRRect(
                            borderRadius: BorderRadius.circular(4),
                            child: LinearProgressIndicator(
                              value: _progress,
                              minHeight: 4,
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
