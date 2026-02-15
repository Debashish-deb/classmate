import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../features/onboarding/pages/onboarding_page.dart';
import '../../features/recording/pages/recording_page.dart';
import '../../features/sessions/pages/sessions_page.dart';
import '../../features/notes/pages/notes_page.dart';
import '../../features/settings/pages/settings_page.dart';
import '../../features/export/pages/export_page.dart';
import '../../features/processing/pages/processing_page.dart';

final appRouterProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    initialLocation: '/onboarding',
    routes: [
      // Onboarding
      GoRoute(
        path: '/onboarding',
        name: 'onboarding',
        builder: (context, state) => const OnboardingPage(),
      ),
      
      // Main app with bottom navigation
      ShellRoute(
        builder: (context, state, child) {
          return MainNavigation(child: child);
        },
        routes: [
          GoRoute(
            path: '/recording',
            name: 'recording',
            builder: (context, state) => const RecordingPage(),
          ),
          GoRoute(
            path: '/sessions',
            name: 'sessions',
            builder: (context, state) => const SessionsPage(),
          ),
          GoRoute(
            path: '/notes',
            name: 'notes',
            builder: (context, state) => const NotesPage(),
          ),
          GoRoute(
            path: '/settings',
            name: 'settings',
            builder: (context, state) => const SettingsPage(),
          ),
        ],
      ),
      
      // Processing page (modal)
      GoRoute(
        path: '/processing/:sessionId',
        name: 'processing',
        builder: (context, state) {
          final sessionId = state.pathParameters['sessionId']!;
          return ProcessingPage(sessionId: sessionId);
        },
      ),
      
      // Export page
      GoRoute(
        path: '/export/:sessionId',
        name: 'export',
        builder: (context, state) {
          final sessionId = state.pathParameters['sessionId']!;
          return ExportPage(sessionId: sessionId);
        },
      ),
    ],
    errorBuilder: (context, state) => ErrorPage(error: state.error),
  );
});

class MainNavigation extends ConsumerStatefulWidget {
  final Widget child;
  
  const MainNavigation({super.key, required this.child});

  @override
  ConsumerState<MainNavigation> createState() => _MainNavigationState();
}

class _MainNavigationState extends ConsumerState<MainNavigation> {
  int _currentIndex = 0;

  final List<NavigationItem> _navigationItems = [
    NavigationItem(
      icon: Icons.mic,
      label: 'Record',
      route: '/recording',
    ),
    NavigationItem(
      icon: Icons.history,
      label: 'Sessions',
      route: '/sessions',
    ),
    NavigationItem(
      icon: Icons.note,
      label: 'Notes',
      route: '/notes',
    ),
    NavigationItem(
      icon: Icons.settings,
      label: 'Settings',
      route: '/settings',
    ),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: widget.child,
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _currentIndex,
        onTap: (index) {
          setState(() {
            _currentIndex = index;
          });
          context.go(_navigationItems[index].route);
        },
        items: _navigationItems
            .map((item) => BottomNavigationBarItem(
                  icon: Icon(item.icon),
                  label: item.label,
                ))
            .toList(),
      ),
    );
  }
}

class NavigationItem {
  final IconData icon;
  final String label;
  final String route;

  NavigationItem({
    required this.icon,
    required this.label,
    required this.route,
  });
}

class ErrorPage extends StatelessWidget {
  final Exception? error;
  
  const ErrorPage({super.key, this.error});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Error'),
      ),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(
                Icons.error_outline,
                size: 64,
                color: Colors.red,
              ),
              const SizedBox(height: 16),
              const Text(
                'An error occurred',
                style: TextStyle(
                  fontSize: 24,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                error?.toString() ?? 'Unknown error',
                textAlign: TextAlign.center,
                style: const TextStyle(color: Colors.grey),
              ),
              const SizedBox(height: 24),
              ElevatedButton(
                onPressed: () => context.go('/recording'),
                child: const Text('Go Home'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
