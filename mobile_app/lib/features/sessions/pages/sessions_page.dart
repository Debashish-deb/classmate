import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import '../../../shared/services/session_manager.dart';

final sessionManagerProvider = Provider<SessionManager>((ref) => SessionManager());

class SessionsPage extends ConsumerStatefulWidget {
  const SessionsPage({super.key});

  @override
  ConsumerState<SessionsPage> createState() => _SessionsPageState();
}

class _SessionsPageState extends ConsumerState<SessionsPage> {
  final ScrollController _scrollController = ScrollController();
  List<Session> _sessions = [];
  bool _isLoading = true;
  String _searchQuery = '';
  SessionStatus? _filterStatus;

  @override
  void initState() {
    super.initState();
    _loadSessions();
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  Future<void> _loadSessions() async {
    setState(() {
      _isLoading = true;
    });

    try {
      final sessionManager = ref.read(sessionManagerProvider);
      await sessionManager.initialize();
      
      final sessions = await sessionManager.getAllSessions();
      setState(() {
        _sessions = sessions;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _isLoading = false;
      });
      _showError('Failed to load sessions: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Sessions'),
        actions: [
          IconButton(
            icon: const Icon(Icons.filter_list),
            onPressed: _showFilterDialog,
          ),
        ],
      ),
      body: Column(
        children: [
          _buildSearchBar(),
          _buildFilterChips(),
          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator())
                : _sessions.isEmpty
                    ? _buildEmptyState()
                    : _buildSessionsList(),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => context.go('/recording'),
        child: const Icon(Icons.add),
      ),
    );
  }

  Widget _buildSearchBar() {
    return Padding(
      padding: const EdgeInsets.all(16.0),
      child: TextField(
        decoration: InputDecoration(
          hintText: 'Search sessions...',
          prefixIcon: const Icon(Icons.search),
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
          ),
        ),
        onChanged: (value) {
          setState(() {
            _searchQuery = value.toLowerCase();
          });
        },
      ),
    );
  }

  Widget _buildFilterChips() {
    if (_filterStatus == null) return const SizedBox.shrink();
    
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16.0),
      child: Wrap(
        spacing: 8,
        children: [
          Chip(
            label: Text(_getStatusLabel(_filterStatus!)),
            deleteIcon: const Icon(Icons.close, size: 18),
            onDeleted: () {
              setState(() {
                _filterStatus = null;
              });
            },
          ),
        ],
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.mic_none,
              size: 64,
              color: Colors.grey[400],
            ),
            const SizedBox(height: 16),
            Text(
              'No sessions yet',
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                color: Colors.grey[600],
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Start recording your first lecture',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: Colors.grey[500],
              ),
            ),
            const SizedBox(height: 24),
            ElevatedButton.icon(
              onPressed: () => context.go('/recording'),
              icon: const Icon(Icons.mic),
              label: const Text('Start Recording'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSessionsList() {
    final filteredSessions = _getFilteredSessions();
    
    return RefreshIndicator(
      onRefresh: _loadSessions,
      child: ListView.builder(
        controller: _scrollController,
        padding: const EdgeInsets.all(16.0),
        itemCount: filteredSessions.length,
        itemBuilder: (context, index) {
          final session = filteredSessions[index];
          return SessionCard(
            session: session,
            onTap: () => _openSession(session),
            onDelete: () => _deleteSession(session),
          );
        },
      ),
    );
  }

  List<Session> _getFilteredSessions() {
    if (_searchQuery.isEmpty) return _sessions;
    
    return _sessions.where((session) =>
        session.title.toLowerCase().contains(_searchQuery.toLowerCase()) ||
        session.transcript?.toLowerCase().contains(_searchQuery.toLowerCase()) == true ||
        session.summary?.toLowerCase().contains(_searchQuery.toLowerCase()) == true
    ).toList();
  }

  void _openSession(Session session) {
    if (session.hasNotes) {
      context.go('/notes/${session.id}');
    } else if (session.isProcessing) {
      context.go('/processing/${session.id}');
    } else {
      _showSessionOptions(session);
    }
  }

  void _showSessionOptions(Session session) {
    showModalBottomSheet(
      context: context,
      builder: (context) => SessionOptionsSheet(
        session: session,
        onNotes: () {
          Navigator.pop(context);
          context.go('/notes/${session.id}');
        },
        onExport: () {
          Navigator.pop(context);
          context.go('/export/${session.id}');
        },
        onDelete: () {
          Navigator.pop(context);
          _deleteSession(session);
        },
      ),
    );
  }

  Future<void> _deleteSession(Session session) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Session'),
        content: Text('Are you sure you want to delete "${session.title}"? This action cannot be undone.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            child: const Text('Delete'),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      try {
        final sessionManager = ref.read(sessionManagerProvider);
        await sessionManager.deleteSession(session.id);
        await _loadSessions();
        _showSuccess('Session deleted');
      } catch (e) {
        _showError('Failed to delete session: $e');
      }
    }
  }

  void _showFilterDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Filter Sessions'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: SessionStatus.values.map((status) {
            return RadioListTile<SessionStatus>(
              title: Text(_getStatusLabel(status)),
              value: status,
              groupValue: _filterStatus,
              onChanged: (value) {
                setState(() {
                  _filterStatus = value;
                });
                Navigator.pop(context);
              },
            );
          }).toList(),
        ),
        actions: [
          TextButton(
            onPressed: () {
              setState(() {
                _filterStatus = null;
              });
              Navigator.pop(context);
            },
            child: const Text('Clear Filter'),
          ),
        ],
      ),
    );
  }

  String _getStatusLabel(SessionStatus status) {
    switch (status) {
      case SessionStatus.recording:
        return 'Recording';
      case SessionStatus.processing:
        return 'Processing';
      case SessionStatus.completed:
        return 'Completed';
      case SessionStatus.failed:
        return 'Failed';
      case SessionStatus.uploaded:
        return 'Uploaded';
    }
  }

  void _showSuccess(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message), backgroundColor: Colors.green),
    );
  }

  void _showError(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message), backgroundColor: Colors.red),
    );
  }
}

class SessionCard extends StatelessWidget {
  final Session session;
  final VoidCallback onTap;
  final VoidCallback onDelete;

  const SessionCard({
    super.key,
    required this.session,
    required this.onTap,
    required this.onDelete,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      session.title,
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                  _buildStatusChip(),
                ],
              ),
              const SizedBox(height: 8),
              Text(
                DateFormat('MMM d, yyyy • h:mm a').format(session.startTime),
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: Colors.grey[600],
                ),
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  Icon(Icons.schedule, size: 16, color: Colors.grey[600]),
                  const SizedBox(width: 4),
                  Text(
                    _formatDuration(session.duration),
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: Colors.grey[600],
                    ),
                  ),
                  if (session.hasNotes) ...[
                    const SizedBox(width: 16),
                    Icon(Icons.note, size: 16, color: Colors.green[600]),
                    const SizedBox(width: 4),
                    Text(
                      'Notes available',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: Colors.green[600],
                      ),
                    ),
                  ],
                ],
              ),
              if (session.isProcessing) ...[
                const SizedBox(height: 12),
                LinearProgressIndicator(
                  value: session.uploadProgress,
                  backgroundColor: Colors.grey[300],
                  valueColor: AlwaysStoppedAnimation<Color>(
                    Theme.of(context).colorScheme.primary,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  'Processing: ${(session.uploadProgress * 100).toInt()}%',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildStatusChip() {
    Color color;
    String label;
    
    switch (session.status) {
      case SessionStatus.recording:
        color = Colors.red;
        label = 'Recording';
        break;
      case SessionStatus.processing:
        color = Colors.orange;
        label = 'Processing';
        break;
      case SessionStatus.completed:
        color = Colors.green;
        label = 'Completed';
        break;
      case SessionStatus.failed:
        color = Colors.red;
        label = 'Failed';
        break;
      case SessionStatus.uploaded:
        color = Colors.blue;
        label = 'Uploaded';
        break;
    }
    
    return Chip(
      label: Text(
        label,
        style: const TextStyle(fontSize: 12, color: Colors.white),
      ),
      backgroundColor: color,
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
    );
  }

  String _formatDuration(Duration duration) {
    final hours = duration.inHours;
    final minutes = duration.inMinutes % 60;
    
    if (hours > 0) {
      return '${hours}h ${minutes}m';
    } else {
      return '${minutes}m';
    }
  }
}

class SessionOptionsSheet extends StatelessWidget {
  final Session session;
  final VoidCallback onNotes;
  final VoidCallback onExport;
  final VoidCallback onDelete;

  const SessionOptionsSheet({
    super.key,
    required this.session,
    required this.onNotes,
    required this.onExport,
    required this.onDelete,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          ListTile(
            leading: const Icon(Icons.note),
            title: const Text('View Notes'),
            onTap: onNotes,
          ),
          ListTile(
            leading: const Icon(Icons.share),
            title: const Text('Export'),
            onTap: onExport,
          ),
          ListTile(
            leading: const Icon(Icons.delete, color: Colors.red),
            title: const Text('Delete', style: TextStyle(color: Colors.red)),
            onTap: onDelete,
          ),
        ],
      ),
    );
  }
}
