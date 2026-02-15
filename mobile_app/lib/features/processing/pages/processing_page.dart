import 'package:flutter/material.dart';

class ProcessingPage extends StatelessWidget {
  final String sessionId;
  
  const ProcessingPage({super.key, required this.sessionId});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Processing'),
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const CircularProgressIndicator(),
            const SizedBox(height: 16),
            Text('Processing session: $sessionId'),
            const SizedBox(height: 8),
            const Text('AI transcription in progress...'),
          ],
        ),
      ),
    );
  }
}