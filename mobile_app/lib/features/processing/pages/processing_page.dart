import 'dart:async';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../../shared/services/api_client.dart';

enum ProcessingStatus { polling, completed, failed, timedOut }

class ProcessingPage extends StatefulWidget {
  final String sessionId;

  const ProcessingPage({super.key, required this.sessionId});

  @override
  State<ProcessingPage> createState() => _ProcessingPageState();
}

class _ProcessingPageState extends State<ProcessingPage> {
  final ApiClient _apiClient = ApiClient();
  Timer? _pollTimer;
  ProcessingStatus _status = ProcessingStatus.polling;
  String _statusMessage = 'AI transcription in progress...';
  int _pollCount = 0;
  String? _errorMessage;

  static const Duration _pollInterval = Duration(seconds: 30);
  static const int _maxPolls = 20; // 20 * 30s = 10 minutes timeout

  @override
  void initState() {
    super.initState();
    _startPolling();
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    super.dispose();
  }

  void _startPolling() {
    _pollCount = 0;
    setState(() {
      _status = ProcessingStatus.polling;
      _statusMessage = 'AI transcription in progress...';
      _errorMessage = null;
    });
    // Poll immediately, then on interval
    _checkSessionStatus();
    _pollTimer = Timer.periodic(_pollInterval, (_) => _checkSessionStatus());
  }

  Future<void> _checkSessionStatus() async {
    _pollCount++;
    if (_pollCount > _maxPolls) {
      _pollTimer?.cancel();
      setState(() {
        _status = ProcessingStatus.timedOut;
        _statusMessage = 'Processing is taking longer than expected.';
      });
      return;
    }

    try {
      final session = await _apiClient.getSession(widget.sessionId);
      if (session == null) {
        setState(() {
          _statusMessage = 'Checking status... (attempt $_pollCount)';
        });
        return;
      }

      if (session.isCompleted) {
        _pollTimer?.cancel();
        setState(() {
          _status = ProcessingStatus.completed;
          _statusMessage = 'Transcription complete!';
        });
      } else if (session.status.name == 'failed') {
        _pollTimer?.cancel();
        setState(() {
          _status = ProcessingStatus.failed;
          _statusMessage = 'Transcription failed.';
          _errorMessage = 'The server encountered an error processing your recording.';
        });
      } else {
        final progress = session.uploadProgress;
        setState(() {
          _statusMessage = progress > 0
              ? 'Processing... ${(progress * 100).toStringAsFixed(0)}% chunks uploaded'
              : 'Waiting for transcription... (attempt $_pollCount)';
        });
      }
    } catch (e) {
      setState(() {
        _statusMessage = 'Checking status... (attempt $_pollCount)';
      });
    }
  }

  void _retry() {
    _pollTimer?.cancel();
    _startPolling();
  }

  void _cancel() {
    _pollTimer?.cancel();
    context.go('/recording');
  }

  void _viewNotes() {
    context.go('/sessions');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Processing'),
        leading: IconButton(
          icon: const Icon(Icons.close),
          onPressed: _cancel,
        ),
      ),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(32.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              _buildStatusIcon(),
              const SizedBox(height: 24),
              Text(
                _statusMessage,
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.titleMedium,
              ),
              if (_errorMessage != null) ...[
                const SizedBox(height: 8),
                Text(
                  _errorMessage!,
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Colors.red,
                  ),
                ),
              ],
              const SizedBox(height: 12),
              Text(
                'Session: ${widget.sessionId.substring(0, 8)}...',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: Colors.grey,
                ),
              ),
              const SizedBox(height: 32),
              _buildActions(),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildStatusIcon() {
    switch (_status) {
      case ProcessingStatus.polling:
        return const SizedBox(
          width: 64,
          height: 64,
          child: CircularProgressIndicator(strokeWidth: 4),
        );
      case ProcessingStatus.completed:
        return const Icon(Icons.check_circle, color: Colors.green, size: 64);
      case ProcessingStatus.failed:
        return const Icon(Icons.error, color: Colors.red, size: 64);
      case ProcessingStatus.timedOut:
        return const Icon(Icons.timer_off, color: Colors.orange, size: 64);
    }
  }

  Widget _buildActions() {
    switch (_status) {
      case ProcessingStatus.polling:
        return TextButton(
          onPressed: _cancel,
          child: const Text('Cancel'),
        );
      case ProcessingStatus.completed:
        return ElevatedButton.icon(
          onPressed: _viewNotes,
          icon: const Icon(Icons.notes),
          label: const Text('View Notes'),
        );
      case ProcessingStatus.failed:
      case ProcessingStatus.timedOut:
        return Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            OutlinedButton(
              onPressed: _cancel,
              child: const Text('Go Back'),
            ),
            const SizedBox(width: 16),
            ElevatedButton.icon(
              onPressed: _retry,
              icon: const Icon(Icons.refresh),
              label: const Text('Retry'),
            ),
          ],
        );
    }
  }
}