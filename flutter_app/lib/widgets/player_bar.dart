import 'package:flutter/material.dart';
import 'package:just_audio/just_audio.dart';

class PlayerBar extends StatelessWidget {
  final AudioPlayer player;
  final bool loading;
  final bool hasAudio;
  final VoidCallback onGenerate;

  const PlayerBar({
    super.key,
    required this.player,
    required this.loading,
    required this.hasAudio,
    required this.onGenerate,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        FilledButton.icon(
          onPressed: loading ? null : onGenerate,
          icon: loading
              ? const SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Icon(Icons.auto_awesome),
          label: Text(loading ? 'Generating…' : 'Generate & Play'),
        ),
        const SizedBox(width: 12),
        StreamBuilder<PlayerState>(
          stream: player.playerStateStream,
          builder: (context, snapshot) {
            final state = snapshot.data;
            final playing = state?.playing ?? false;
            final processing = state?.processingState;

            if (!hasAudio) {
              return const SizedBox.shrink();
            }

            if (processing == ProcessingState.completed) {
              return IconButton(
                tooltip: 'Replay',
                onPressed: () => player.seek(Duration.zero),
                icon: const Icon(Icons.replay),
              );
            }

            return IconButton(
              tooltip: playing ? 'Pause' : 'Play',
              onPressed: () {
                if (playing) {
                  player.pause();
                } else {
                  player.play();
                }
              },
              icon: Icon(
                playing ? Icons.pause_circle : Icons.play_circle,
                size: 38,
              ),
            );
          },
        ),
        Expanded(
          child: StreamBuilder<Duration>(
            stream: player.positionStream,
            builder: (context, snapshot) {
              final position = snapshot.data ?? Duration.zero;
              final duration = player.duration ?? Duration.zero;

              final max = duration.inMilliseconds.toDouble();
              final value = position.inMilliseconds
                  .clamp(0, duration.inMilliseconds)
                  .toDouble();

              return Slider(
                min: 0,
                max: max <= 0 ? 1 : max,
                value: max <= 0 ? 0 : value,
                onChanged: max <= 0
                    ? null
                    : (v) => player.seek(
                          Duration(milliseconds: v.round()),
                        ),
              );
            },
          ),
        ),
        IconButton(
          tooltip: 'Stop',
          onPressed: hasAudio ? player.stop : null,
          icon: const Icon(Icons.stop_circle_outlined),
        ),
      ],
    );
  }
}
