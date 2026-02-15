import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

class RecordingButton extends ConsumerStatefulWidget {
  final VoidCallback? onStart;
  final VoidCallback? onStop;
  final bool isRecording;
  final Duration? duration;
  final bool enabled;

  const RecordingButton({
    super.key,
    this.onStart,
    this.onStop,
    this.isRecording = false,
    this.duration,
    this.enabled = true,
  });

  @override
  ConsumerState<RecordingButton> createState() => _RecordingButtonState();
}

class _RecordingButtonState extends ConsumerState<RecordingButton>
    with TickerProviderStateMixin {
  late AnimationController _pulseController;
  late AnimationController _scaleController;
  late Animation<double> _pulseAnimation;
  late Animation<double> _scaleAnimation;

  @override
  void initState() {
    super.initState();
    
    _pulseController = AnimationController(
      duration: const Duration(seconds: 1),
      vsync: this,
    );
    
    _scaleController = AnimationController(
      duration: const Duration(milliseconds: 200),
      vsync: this,
    );

    _pulseAnimation = Tween<double>(
      begin: 1.0,
      end: 1.1,
    ).animate(CurvedAnimation(
      parent: _pulseController,
      curve: Curves.easeInOut,
    ));

    _scaleAnimation = Tween<double>(
      begin: 1.0,
      end: 0.95,
    ).animate(CurvedAnimation(
      parent: _scaleController,
      curve: Curves.easeInOut,
    ));

    if (widget.isRecording) {
      _pulseController.repeat(reverse: true);
    }
  }

  @override
  void didUpdateWidget(RecordingButton oldWidget) {
    super.didUpdateWidget(oldWidget);
    
    if (widget.isRecording != oldWidget.isRecording) {
      if (widget.isRecording) {
        _pulseController.repeat(reverse: true);
      } else {
        _pulseController.stop();
        _pulseController.reset();
      }
    }
  }

  @override
  void dispose() {
    _pulseController.dispose();
    _scaleController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        AnimatedBuilder(
          animation: Listenable.merge([_pulseAnimation, _scaleAnimation]),
          builder: (context, child) {
            return Transform.scale(
              scale: widget.isRecording ? _pulseAnimation.value : _scaleAnimation.value,
              child: GestureDetector(
                onTap: widget.enabled ? _handleTap : null,
                child: Container(
                  width: 80,
                  height: 80,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: widget.isRecording 
                        ? Theme.of(context).colorScheme.error
                        : widget.enabled 
                            ? Theme.of(context).colorScheme.primary
                            : Colors.grey,
                    boxShadow: [
                      BoxShadow(
                        color: widget.isRecording 
                            ? Theme.of(context).colorScheme.error.withOpacity(0.3)
                            : Theme.of(context).colorScheme.primary.withOpacity(0.3),
                        blurRadius: widget.isRecording ? 20 : 10,
                        spreadRadius: widget.isRecording ? 2 : 0,
                      ),
                    ],
                  ),
                  child: Icon(
                    widget.isRecording ? Icons.stop : Icons.mic,
                    color: Colors.white,
                    size: 32,
                  ),
                ),
              ),
            );
          },
        ),
        const SizedBox(height: 16),
        if (widget.duration != null)
          _buildDurationDisplay(),
        if (!widget.enabled)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text(
              'Permissions Required',
              style: TextStyle(
                color: Theme.of(context).colorScheme.error,
                fontSize: 12,
              ),
            ),
          ),
      ],
    );
  }

  Widget _buildDurationDisplay() {
    final duration = widget.duration!;
    final minutes = duration.inMinutes.toString().padLeft(2, '0');
    final seconds = (duration.inSeconds % 60).toString().padLeft(2, '0');
    
    return Text(
      '$minutes:$seconds',
      style: TextStyle(
        fontSize: 18,
        fontWeight: FontWeight.w600,
        color: widget.isRecording 
            ? Theme.of(context).colorScheme.error
            : Theme.of(context).colorScheme.onSurface,
      ),
    );
  }

  void _handleTap() async {
    if (!widget.enabled) return;

    _scaleController.forward().then((_) {
      _scaleController.reverse();
    });

    if (widget.isRecording) {
      widget.onStop?.call();
    } else {
      widget.onStart?.call();
    }
  }
}
