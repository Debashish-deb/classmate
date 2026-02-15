import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:logger/logger.dart';

class SettingsPage extends ConsumerStatefulWidget {
  const SettingsPage({super.key});

  @override
  ConsumerState<SettingsPage> createState() => _SettingsPageState();
}

class _SettingsPageState extends ConsumerState<SettingsPage> {
  final Logger _logger = Logger();
  late SharedPreferences _prefs;
  
  // Settings state
  bool _autoTranscribe = true;
  bool _speakerIdentification = true;
  bool _cloudSync = true;
  bool _notifications = true;
  bool _darkMode = false;
  String _audioQuality = 'medium';
  String _summaryLength = 'medium';
  String _storageLocation = 'cloud';
  String _apiKey = '';
  String _apiUrl = 'http://localhost:8000';

  @override
  void initState() {
    super.initState();
    _loadSettings();
  }

  Future<void> _loadSettings() async {
    _prefs = await SharedPreferences.getInstance();
    setState(() {
      _autoTranscribe = _prefs.getBool('auto_transcribe') ?? true;
      _speakerIdentification = _prefs.getBool('speaker_identification') ?? true;
      _cloudSync = _prefs.getBool('cloud_sync') ?? true;
      _notifications = _prefs.getBool('notifications') ?? true;
      _darkMode = _prefs.getBool('dark_mode') ?? false;
      _audioQuality = _prefs.getString('audio_quality') ?? 'medium';
      _summaryLength = _prefs.getString('summary_length') ?? 'medium';
      _storageLocation = _prefs.getString('storage_location') ?? 'cloud';
      _apiKey = _prefs.getString('api_key') ?? '';
      _apiUrl = _prefs.getString('api_url') ?? 'http://localhost:8000';
    });
  }

  Future<void> _saveSetting(String key, dynamic value) async {
    await _prefs.setBool(key, value);
    _logger.i('Setting saved: $key = $value');
  }

  Future<void> _saveStringSetting(String key, String value) async {
    await _prefs.setString(key, value);
    _logger.i('Setting saved: $key = $value');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Settings'),
        backgroundColor: Theme.of(context).colorScheme.surface,
        elevation: 0,
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // Recording Settings
          _buildSection(
            title: 'Recording',
            icon: Icons.mic,
            children: [
              SwitchListTile(
                title: const Text('Auto-transcribe'),
                subtitle: const Text('Automatically transcribe recordings'),
                value: _autoTranscribe,
                onChanged: (value) {
                  setState(() {
                    _autoTranscribe = value;
                  });
                  _saveSetting('auto_transcribe', value);
                },
              ),
              SwitchListTile(
                title: const Text('Speaker Identification'),
                subtitle: const Text('Identify different speakers'),
                value: _speakerIdentification,
                onChanged: (value) {
                  setState(() {
                    _speakerIdentification = value;
                  });
                  _saveSetting('speaker_identification', value);
                },
              ),
              ListTile(
                title: const Text('Audio Quality'),
                subtitle: Text(_audioQuality.toUpperCase()),
                trailing: const Icon(Icons.chevron_right),
                onTap: () => _showAudioQualityDialog(),
              ),
            ],
          ),

          const SizedBox(height: 24),

          // AI Assistant Settings
          _buildSection(
            title: 'AI Assistant',
            icon: Icons.psychology,
            children: [
              ListTile(
                title: const Text('Summary Length'),
                subtitle: Text(_summaryLength.toUpperCase()),
                trailing: const Icon(Icons.chevron_right),
                onTap: () => _showSummaryLengthDialog(),
              ),
              SwitchListTile(
                title: const Text('Key Points'),
                subtitle: const Text('Extract key points from transcripts'),
                value: true, // Always enabled for now
                onChanged: null,
              ),
              SwitchListTile(
                title: const Text('Action Items'),
                subtitle: const Text('Identify action items'),
                value: true, // Always enabled for now
                onChanged: null,
              ),
            ],
          ),

          const SizedBox(height: 24),

          // Storage & Sync
          _buildSection(
            title: 'Storage & Sync',
            icon: Icons.storage,
            children: [
              SwitchListTile(
                title: const Text('Cloud Sync'),
                subtitle: const Text('Sync recordings and notes to cloud'),
                value: _cloudSync,
                onChanged: (value) {
                  setState(() {
                    _cloudSync = value;
                  });
                  _saveSetting('cloud_sync', value);
                },
              ),
              ListTile(
                title: const Text('Storage Location'),
                subtitle: Text(_storageLocation.toUpperCase()),
                trailing: const Icon(Icons.chevron_right),
                onTap: () => _showStorageLocationDialog(),
              ),
            ],
          ),

          const SizedBox(height: 24),

          // Notifications
          _buildSection(
            title: 'Notifications',
            icon: Icons.notifications,
            children: [
              SwitchListTile(
                title: const Text('Push Notifications'),
                subtitle: const Text('Receive notifications for completed transcriptions'),
                value: _notifications,
                onChanged: (value) {
                  setState(() {
                    _notifications = value;
                  });
                  _saveSetting('notifications', value);
                },
              ),
            ],
          ),

          const SizedBox(height: 24),

          // Appearance
          _buildSection(
            title: 'Appearance',
            icon: Icons.palette,
            children: [
              SwitchListTile(
                title: const Text('Dark Mode'),
                subtitle: const Text('Use dark theme'),
                value: _darkMode,
                onChanged: (value) {
                  setState(() {
                    _darkMode = value;
                  });
                  _saveSetting('dark_mode', value);
                },
              ),
            ],
          ),

          const SizedBox(height: 24),

          // Advanced Settings
          _buildSection(
            title: 'Advanced',
            icon: Icons.settings,
            children: [
              ListTile(
                title: const Text('API URL'),
                subtitle: Text(_apiUrl),
                trailing: const Icon(Icons.edit),
                onTap: () => _showApiUrlDialog(),
              ),
              ListTile(
                title: const Text('API Key'),
                subtitle: const Text('Configure API key for advanced features'),
                trailing: const Icon(Icons.key),
                onTap: () => _showApiKeyDialog(),
              ),
              ListTile(
                title: const Text('Clear Cache'),
                subtitle: const Text('Clear local cache and temporary files'),
                trailing: const Icon(Icons.delete_outline),
                onTap: () => _showClearCacheDialog(),
              ),
              ListTile(
                title: const Text('Export Data'),
                subtitle: const Text('Export all recordings and notes'),
                trailing: const Icon(Icons.download),
                onTap: () => _showExportDataDialog(),
              ),
            ],
          ),

          const SizedBox(height: 24),

          // About
          _buildSection(
            title: 'About',
            icon: Icons.info,
            children: [
              ListTile(
                title: const Text('Version'),
                subtitle: const Text('1.0.0'),
                trailing: const Icon(Icons.info_outline),
              ),
              ListTile(
                title: const Text('Privacy Policy'),
                subtitle: const Text('View our privacy policy'),
                trailing: const Icon(Icons.open_in_new),
                onTap: () => _launchUrl('https://classmate.app/privacy'),
              ),
              ListTile(
                title: const Text('Terms of Service'),
                subtitle: const Text('View our terms of service'),
                trailing: const Icon(Icons.open_in_new),
                onTap: () => _launchUrl('https://classmate.app/terms'),
              ),
              ListTile(
                title: const Text('Help & Support'),
                subtitle: const Text('Get help with ClassMate'),
                trailing: const Icon(Icons.help_outline),
                onTap: () => _launchUrl('https://classmate.app/support'),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildSection({
    required String title,
    required IconData icon,
    required List<Widget> children,
  }) {
    return Container(
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(12),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 10,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                Icon(
                  icon,
                  color: Theme.of(context).colorScheme.primary,
                  size: 24,
                ),
                const SizedBox(width: 12),
                Text(
                  title,
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
          ...children,
        ],
      ),
    );
  }

  void _showAudioQualityDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Audio Quality'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            RadioListTile(
              title: const Text('Low'),
              subtitle: const Text('Smaller files, lower quality'),
              value: 'low',
              groupValue: _audioQuality,
              onChanged: (value) {
                setState(() {
                  _audioQuality = value!;
                });
                _saveStringSetting('audio_quality', value!);
                Navigator.pop(context);
              },
            ),
            RadioListTile(
              title: const Text('Medium'),
              subtitle: const Text('Balanced quality and size'),
              value: 'medium',
              groupValue: _audioQuality,
              onChanged: (value) {
                setState(() {
                  _audioQuality = value!;
                });
                _saveStringSetting('audio_quality', value!);
                Navigator.pop(context);
              },
            ),
            RadioListTile(
              title: const Text('High'),
              subtitle: const Text('Best quality, larger files'),
              value: 'high',
              groupValue: _audioQuality,
              onChanged: (value) {
                setState(() {
                  _audioQuality = value!;
                });
                _saveStringSetting('audio_quality', value!);
                Navigator.pop(context);
              },
            ),
          ],
        ),
      ),
    );
  }

  void _showSummaryLengthDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Summary Length'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            RadioListTile(
              title: const Text('Short'),
              subtitle: const Text('Brief summaries'),
              value: 'short',
              groupValue: _summaryLength,
              onChanged: (value) {
                setState(() {
                  _summaryLength = value!;
                });
                _saveStringSetting('summary_length', value!);
                Navigator.pop(context);
              },
            ),
            RadioListTile(
              title: const Text('Medium'),
              subtitle: const Text('Detailed summaries'),
              value: 'medium',
              groupValue: _summaryLength,
              onChanged: (value) {
                setState(() {
                  _summaryLength = value!;
                });
                _saveStringSetting('summary_length', value!);
                Navigator.pop(context);
              },
            ),
            RadioListTile(
              title: const Text('Long'),
              subtitle: const Text('Comprehensive summaries'),
              value: 'long',
              groupValue: _summaryLength,
              onChanged: (value) {
                setState(() {
                  _summaryLength = value!;
                });
                _saveStringSetting('summary_length', value!);
                Navigator.pop(context);
              },
            ),
          ],
        ),
      ),
    );
  }

  void _showStorageLocationDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Storage Location'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            RadioListTile(
              title: const Text('Cloud'),
              subtitle: const Text('Store in the cloud'),
              value: 'cloud',
              groupValue: _storageLocation,
              onChanged: (value) {
                setState(() {
                  _storageLocation = value!;
                });
                _saveStringSetting('storage_location', value!);
                Navigator.pop(context);
              },
            ),
            RadioListTile(
              title: const Text('Local'),
              subtitle: const Text('Store on device only'),
              value: 'local',
              groupValue: _storageLocation,
              onChanged: (value) {
                setState(() {
                  _storageLocation = value!;
                });
                _saveStringSetting('storage_location', value!);
                Navigator.pop(context);
              },
            ),
          ],
        ),
      ),
    );
  }

  void _showApiUrlDialog() {
    final controller = TextEditingController(text: _apiUrl);
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('API URL'),
        content: TextField(
          controller: controller,
          decoration: const InputDecoration(
            labelText: 'API URL',
            hintText: 'http://localhost:8000',
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () {
              setState(() {
                _apiUrl = controller.text;
              });
              _saveStringSetting('api_url', controller.text);
              Navigator.pop(context);
            },
            child: const Text('Save'),
          ),
        ],
      ),
    );
  }

  void _showApiKeyDialog() {
    final controller = TextEditingController(text: _apiKey);
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('API Key'),
        content: TextField(
          controller: controller,
          decoration: const InputDecoration(
            labelText: 'API Key',
            hintText: 'Enter your API key',
          ),
          obscureText: true,
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () {
              setState(() {
                _apiKey = controller.text;
              });
              _saveStringSetting('api_key', controller.text);
              Navigator.pop(context);
            },
            child: const Text('Save'),
          ),
        ],
      ),
    );
  }

  void _showClearCacheDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Clear Cache'),
        content: const Text('Are you sure you want to clear all cache? This action cannot be undone.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () {
              // TODO: Implement cache clearing
              Navigator.pop(context);
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('Cache cleared successfully')),
              );
            },
            child: const Text('Clear'),
          ),
        ],
      ),
    );
  }

  void _showExportDataDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Export Data'),
        content: const Text('Choose export format:'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () {
              // TODO: Implement data export
              Navigator.pop(context);
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('Export started')),
              );
            },
            child: const Text('JSON'),
          ),
          TextButton(
            onPressed: () {
              // TODO: Implement data export
              Navigator.pop(context);
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('Export started')),
              );
            },
            child: const Text('CSV'),
          ),
        ],
      ),
    );
  }

  void _launchUrl(String url) {
    // TODO: Implement URL launcher
    _logger.i('Launching URL: $url');
  }
}