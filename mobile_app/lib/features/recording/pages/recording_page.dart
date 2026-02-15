import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../shared/services/recording_service.dart';
import '../../../shared/services/session_manager.dart';
import '../../../shared/services/upload_queue_service.dart';
import '../../../shared/widgets/recording_button.dart';
import '../../../shared/models/session_model.dart';

final recordingServiceProvider = Provider<RecordingService>((ref) => RecordingService());
final sessionManagerProvider = Provider<SessionManager>((ref) => SessionManager());
final uploadQueueServiceProvider = Provider<UploadQueueService>((ref) => UploadQueueService());

class RecordingPage extends ConsumerStatefulWidget {
  const RecordingPage({super.key});

  @override
  ConsumerState<RecordingPage> createState() => _RecordingPageState();
}

class _RecordingPageState extends ConsumerState<RecordingPage> {
  Timer? _durationTimer;
  Duration _currentDuration = Duration.zero;
  bool _hasPermissions = false;
  String? _currentSessionId;
  bool _isInitializing = false;

  @override
  void initState() {
    super.initState();
    _initializeServices();
  }

  @override
  void dispose() {
    _durationTimer?.cancel();
    super.dispose();
  }

  Future<void> _initializeServices() async {
    setState(() {
      _isInitializing = true;
    });

    try {
      final recordingService = ref.read(recordingServiceProvider);
      final sessionManager = ref.read(sessionManagerProvider);
      final uploadQueueService = ref.read(uploadQueueServiceProvider);

      await sessionManager.initialize();
      await uploadQueueService.initialize();

      final hasPermissions = await recordingService.requestPermissions();
      
      setState(() {
        _hasPermissions = hasPermissions;
        _isInitializing = false;
      });

      // Check if there's an active recording session
      final currentSession = sessionManager.currentSession;
      if (currentSession != null && currentSession.isRecording) {
        setState(() {
          _currentSessionId = currentSession.id;
        });
        _startDurationTimer();
      }
    } catch (e) {
      setState(() {
        _isInitializing = false;
      });
      _showError('Failed to initialize services: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    final recordingService = ref.read(recordingServiceProvider);
    final sessionManager = ref.read(sessionManagerProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('ClassMate'),
        actions: [
          IconButton(
            icon: const Icon(Icons.history),
            onPressed: () => context.go('/sessions'),
          ),
        ],
      ),
      body: _isInitializing
          ? const Center(child: CircularProgressIndicator())
          : SingleChildScrollView(
              padding: const EdgeInsets.all(24.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  const SizedBox(height: 40),
                  _buildStatusCard(),
                  const SizedBox(height: 40),
                  RecordingButton(
                    isRecording: recordingService.isRecording,
                    duration: _currentDuration,
                    enabled: _hasPermissions,
                    onStart: _startRecording,
                    onStop: _stopRecording,
                  ),
                  const SizedBox(height: 40),
                  if (recordingService.isRecording) ...[
                    _buildRecordingControls(),
                    const SizedBox(height: 20),
                    _buildWaveformPlaceholder(),
                  ],
                  const SizedBox(height: 40),
                  _buildQuickActions(),
                ],
              ),
            ),
    );
  }

  Widget _buildStatusCard() {
    final recordingService = ref.read(recordingServiceProvider);
    
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20.0),
        child: Column(
          children: [
            Icon(
              recordingService.isRecording ? Icons.fiber_manual_record : Icons.mic_none,
              color: recordingService.isRecording ? Colors.red : Colors.grey,
              size: 32,
            ),
            const SizedBox(height: 12),
            Text(
              recordingService.isRecording ? 'Recording in Progress' : 'Ready to Record',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            if (_currentSessionId != null) ...[
              const SizedBox(height: 8),
              Text(
                'Session: ${_currentSessionId?.substring(0, 8)}...',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: Colors.grey[600],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildRecordingControls() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                _buildControlButton(
                  icon: Icons.pause,
                  label: 'Pause',
                  onTap: _pauseRecording,
                ),
                _buildControlButton(
                  icon: Icons.bookmark,
                  label: 'Bookmark',
                  onTap: _addBookmark,
                ),
                _buildControlButton(
                  icon: Icons.note_add,
                  label: 'Quick Note',
                  onTap: _addQuickNote,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildControlButton({
    required IconData icon,
    required String label,
    required VoidCallback onTap,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: Padding(
        padding: const EdgeInsets.all(8.0),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 24),
            const SizedBox(height: 4),
            Text(
              label,
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildWaveformPlaceholder() {
    return Card(
      child: Container(
        height: 120,
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Audio Waveform',
              style: Theme.of(context).textTheme.labelMedium,
            ),
            const SizedBox(height: 8),
            Expanded(
              child: Container(
                decoration: BoxDecoration(
                  color: Colors.grey[100],
                  borderRadius: BorderRadius.circular(4),
                ),
                child: const Center(
                  child: Text(
                    'Waveform visualization\n(coming soon)',
                    textAlign: TextAlign.center,
                    style: TextStyle(color: Colors.grey),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildQuickActions() {
    return Column(
      children: [
        ListTile(
          leading: const Icon(Icons.upload_file),
          title: const Text('Upload Queue'),
          subtitle: const Text('View pending uploads'),
          trailing: const Icon(Icons.chevron_right),
          onTap: () => _showUploadQueue(),
        ),
        ListTile(
          leading: const Icon(Icons.settings),
          title: const Text('Recording Settings'),
          subtitle: const Text('Audio quality, chunk size, etc.'),
          trailing: const Icon(Icons.chevron_right),
          onTap: () => context.go('/settings'),
        ),
      ],
    );
  }

  Future<void> _startRecording() async {
    try {
      final recordingService = ref.read(recordingServiceProvider);
      final sessionManager = ref.read(sessionManagerProvider);

      final session = await sessionManager.createSession(title: 'Recording ${DateTime.now().hour}:${DateTime.now().minute}');
      setState(() {
        _currentSessionId = session.id;
      });

      await recordingService.startRecording(sessionId: session.id);
      _startDurationTimer();

      _showSuccess('Recording started');
    } catch (e) {
      _showError('Failed to start recording: $e');
    }
  }

  Future<void> _stopRecording() async {
    try {
      final recordingService = ref.read(recordingServiceProvider);
      final sessionManager = ref.read(sessionManagerProvider);

      await recordingService.stopRecording();
      await sessionManager.endCurrentSession();
      
      _durationTimer?.cancel();
      setState(() {
        _currentDuration = Duration.zero;
        _currentSessionId = null;
      });

      _showSuccess('Recording stopped and saved');
      
      // Navigate to processing page
      if (_currentSessionId != null) {
        context.go('/processing/$_currentSessionId');
      }
    } catch (e) {
      _showError('Failed to stop recording: $e');
    }
  }

  void _startDurationTimer() {
    _durationTimer?.cancel();
    _durationTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      setState(() {
        _currentDuration = Duration(seconds: timer.tick);
      });
    });
  }

  void _pauseRecording() {
    // TODO: Implement pause functionality
    _showInfo('Pause functionality coming soon');
  }

  void _addBookmark() {
    // TODO: Implement bookmark functionality
    _showInfo('Bookmark added at ${_formatDuration(_currentDuration)}');
  }

  void _addQuickNote() {
    // TODO: Implement quick note functionality
    _showInfo('Quick note feature coming soon');
  }

  void _showUploadQueue() {
    // TODO: Show upload queue dialog
    _showInfo('Upload queue view coming soon');
  }

  String _formatDuration(Duration duration) {
    final minutes = duration.inMinutes.toString().padLeft(2, '0');
    final seconds = (duration.inSeconds % 60).toString().padLeft(2, '0');
    return '$minutes:$seconds';
  }

  void _showSuccess(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Colors.green,
      ),
    );
  }

  void _showError(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Colors.red,
      ),
    );
  }

  void _showInfo(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Colors.blue,
      ),
    );
  }
}
