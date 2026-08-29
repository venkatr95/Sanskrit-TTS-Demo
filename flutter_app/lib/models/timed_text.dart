class TimedSegment {
  final String text;
  final double start;
  final double end;
  final int index;

  const TimedSegment({
    required this.text,
    required this.start,
    required this.end,
    required this.index,
  });

  factory TimedSegment.fromJson(Map<String, dynamic> json) {
    return TimedSegment(
      text: json['text'] as String,
      start: (json['start'] as num).toDouble(),
      end: (json['end'] as num).toDouble(),
      index: json['index'] as int,
    );
  }
}

class TtsResult {
  final String audioUrl;
  final double duration;
  final int sampleRate;
  final List<TimedSegment> segments;

  const TtsResult({
    required this.audioUrl,
    required this.duration,
    required this.sampleRate,
    required this.segments,
  });

  factory TtsResult.fromJson(Map<String, dynamic> json) {
    return TtsResult(
      audioUrl: json['audioUrl'] as String,
      duration: (json['duration'] as num).toDouble(),
      sampleRate: json['sampleRate'] as int,
      segments: (json['segments'] as List)
          .map(
            (e) => TimedSegment.fromJson(
              e as Map<String, dynamic>,
            ),
          )
          .toList(),
    );
  }
}
