import 'package:flutter/material.dart';

class ExportPage extends StatelessWidget {
  final String sessionId;
  
  const ExportPage({super.key, required this.sessionId});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Export'),
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.download, size: 64, color: Colors.grey[400]),
            const SizedBox(height: 16),
            Text('Export session: $sessionId'),
            const SizedBox(height: 8),
            const Text('Export functionality coming soon'),
            const SizedBox(height: 24),
            ElevatedButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Go Back'),
            ),
          ],
        ),
      ),
    );
  }
}