import 'dart:async';

import 'package:flutter/material.dart';

import '../models/timed_text.dart';

class KaraokeText extends StatefulWidget {
  final List<TimedSegment> segments;
  final Stream<Duration> positionStream;

  const KaraokeText({
    super.key,
    required this.segments,
    required this.positionStream,
  });

  @override
  State<KaraokeText> createState() => _KaraokeTextState();
}

class _KaraokeTextState extends State<KaraokeText> {
  final ScrollController _scrollController = ScrollController();
  StreamSubscription<Duration>? _subscription;
  int _active = -1;

  @override
  void initState() {
    super.initState();
    _listenToPosition();
  }

  void _listenToPosition() {
    _subscription?.cancel();
    _subscription = widget.positionStream.listen((position) {
      final seconds = position.inMicroseconds / Duration.microsecondsPerSecond;

      int active = -1;
      for (var i = 0; i < widget.segments.length; i++) {
        final segment = widget.segments[i];
        if (seconds >= segment.start && seconds < segment.end) {
          active = i;
          break;
        }
      }

      if (active != _active) {
        setState(() => _active = active);
        _scrollToActive(active);
      }
    });
  }

  @override
  void didUpdateWidget(covariant KaraokeText oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.positionStream != widget.positionStream) {
      _listenToPosition();
    }
  }

  void _scrollToActive(int index) {
    if (index < 0) return;

    // Estimate item height including margin
    const itemHeight = 90.0;
    
    if (_scrollController.hasClients) {
      // Offset by half the viewport to keep the active item centered
      final viewportHeight = _scrollController.position.viewportDimension;
      final target = (index * itemHeight) - (viewportHeight / 2) + (itemHeight / 2);

      _scrollController.animateTo(
        target.clamp(0.0, _scrollController.position.maxScrollExtent),
        duration: const Duration(milliseconds: 400),
        curve: Curves.easeOutCubic,
      );
    }
  }

  @override
  void dispose() {
    _subscription?.cancel();
    _scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return ListView.builder(
      controller: _scrollController,
      padding: EdgeInsets.symmetric(
        vertical: MediaQuery.of(context).size.height / 3,
        horizontal: 16,
      ),
      itemCount: widget.segments.length,
      itemBuilder: (context, i) {
        final segment = widget.segments[i];
        final active = i == _active;
        final past = i < _active;

        return Container(
          margin: const EdgeInsets.only(bottom: 24),
          alignment: Alignment.center,
          child: AnimatedDefaultTextStyle(
            duration: const Duration(milliseconds: 300),
            curve: Curves.easeOut,
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: active ? 42 : 32,
              height: 1.4,
              fontWeight: active ? FontWeight.bold : FontWeight.w600,
              color: active
                  ? Colors.white
                  : (past ? Colors.white60 : Colors.white30),
              shadows: active
                  ? [
                      Shadow(
                        blurRadius: 24,
                        color: Colors.white.withOpacity(0.4),
                      )
                    ]
                  : null,
            ),
            child: Text(segment.text),
          ),
        );
      },
    );
  }
}
