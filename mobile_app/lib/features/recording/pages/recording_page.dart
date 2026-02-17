import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/theme/app_theme.dart';
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
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      backgroundColor: isDark ? const Color(0xFF0F172A) : const Color(0xFFF8FAFC),
      body: SafeArea(
        child: _isInitializing
            ? _buildLoadingState(context)
            : SingleChildScrollView(
                padding: const EdgeInsets.all(24.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: [
                    const SizedBox(height: 40),
                    _buildHeader(context),
                    const SizedBox(height: 40),
                    _buildStatusCard(context),
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
      ),
    );
  }

  Widget _buildLoadingState(BuildContext context) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            padding: const EdgeInsets.all(24),
            decoration: BoxDecoration(
              gradient: AppTheme.primaryGradient,
              borderRadius: BorderRadius.circular(20),
            ),
            child: const CircularProgressIndicator(
              valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
            ),
          ),
          const SizedBox(height: 24),
          Text(
            'Initializing...',
            style: Theme.of(context).textTheme.titleLarge?.copyWith(
              color: Theme.of(context).colorScheme.primary,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildHeader(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        gradient: AppTheme.primaryGradient,
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: AppTheme.primaryColor.withOpacity(0.3),
            blurRadius: 20,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'ClassMate',
                style: Theme.of(context).textTheme.displayMedium?.copyWith(
                  color: Colors.white,
                  fontWeight: FontWeight.w800,
                ),
              ),
              Row(
                children: [
                  IconButton(
                    onPressed: () => GoRouter.of(context).go('/sessions'),
                    icon: const Icon(Icons.history_rounded, color: Colors.white),
                    style: IconButton.styleFrom(
                      backgroundColor: Colors.white.withOpacity(0.2),
                      padding: const EdgeInsets.all(12),
                    ),
                  ),
                  const SizedBox(width: 8),
                  IconButton(
                    onPressed: _showExitDialog,
                    icon: const Icon(Icons.exit_to_app_rounded, color: Colors.white),
                    style: IconButton.styleFrom(
                      backgroundColor: Colors.white.withOpacity(0.2),
                      padding: const EdgeInsets.all(12),
                    ),
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            'AI-Powered Meeting Assistant',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
              color: Colors.white.withOpacity(0.9),
            ),
          ),
        ],
      ),
    );
  }
  Widget _buildStatusCard(BuildContext context) {
    final recordingService = ref.read(recordingServiceProvider);
    final isDark = Theme.of(context).brightness == Brightness.dark;
    
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        gradient: isDark ? AppTheme.cardGradient : null,
        color: isDark ? null : Colors.white,
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(isDark ? 0.3 : 0.1),
            blurRadius: 20,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: Column(
        children: [
          AnimatedContainer(
            duration: const Duration(milliseconds: 300),
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: recordingService.isRecording 
                  ? AppTheme.errorColor.withOpacity(0.1)
                  : AppTheme.successColor.withOpacity(0.1),
              borderRadius: BorderRadius.circular(16),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                AnimatedSwitcher(
                  duration: const Duration(milliseconds: 300),
                  child: Icon(
                    recordingService.isRecording ? Icons.fiber_manual_record : Icons.mic_none,
                    color: recordingService.isRecording ? AppTheme.errorColor : AppTheme.successColor,
                    size: 32,
                    key: ValueKey(recordingService.isRecording),
                  ),
                ),
                const SizedBox(width: 12),
                Text(
                  recordingService.isRecording ? 'Recording' : 'Ready',
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    color: recordingService.isRecording ? AppTheme.errorColor : AppTheme.successColor,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          Text(
            recordingService.isRecording ? 'Recording in Progress' : 'Ready to Record',
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
              fontWeight: FontWeight.w600,
            ),
          ),
          if (_currentSessionId != null) ...[
            const SizedBox(height: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(
                color: AppTheme.primaryColor.withOpacity(0.1),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                'Session: ${_currentSessionId?.substring(0, 8)}...',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: AppTheme.primaryColor,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ),
          ],
        ],
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
    // Confirmation dialog to prevent accidental stop
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Stop Recording?'),
        content: Text(
          'You have been recording for ${_formatDuration(_currentDuration)}. '
          'Are you sure you want to stop?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Continue Recording'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.red,
              foregroundColor: Colors.white,
            ),
            child: const Text('Stop & Save'),
          ),
        ],
      ),
    );

    if (confirmed != true) return;

    try {
      final recordingService = ref.read(recordingServiceProvider);
      final sessionManager = ref.read(sessionManagerProvider);
      final sessionId = _currentSessionId;

      await recordingService.stopRecording();
      await sessionManager.endCurrentSession();
      
      _durationTimer?.cancel();
      setState(() {
        _currentDuration = Duration.zero;
        _currentSessionId = null;
      });

      _showSuccess('Recording stopped and saved');
      
      // Navigate to processing page
      if (sessionId != null && mounted) {
        context.go('/processing/$sessionId');
      }
    } catch (e) {
      _showError('Failed to stop recording: $e');
    }
  }

  void _startDurationTimer() {
    _durationTimer?.cancel();
    final startTime = DateTime.now();
    _durationTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      setState(() {
        _currentDuration = DateTime.now().difference(startTime);
      });
    });
  }

  Future<void> _pauseRecording() async {
    final recordingService = ref.read(recordingServiceProvider);
    await recordingService.pauseRecording();
    _durationTimer?.cancel();
    _showInfo('Recording paused');
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

  void _showExitDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Exit App'),
        content: const Text('Are you sure you want to exit ClassMate?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(context);
              SystemNavigator.pop();
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: AppTheme.errorColor,
              foregroundColor: Colors.white,
            ),
            child: const Text('Exit'),
          ),
        ],
      ),
    );
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
