import 'package:flutter/material.dart';
import '../services/api_service.dart';

class LeakScreen extends StatelessWidget {
  const LeakScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: FutureBuilder(
        future: ApiService.fetch("leaks"),
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) return const Center(child: CircularProgressIndicator());
          if (!snapshot.hasData || snapshot.hasError) return const Center(child: Text("Failed to load data"));

          final leaks = snapshot.data!['leaks'] as List;
          if (leaks.isEmpty) return const Center(child: Text("No leaks detected"));

          return ListView(
            children: leaks.map<Widget>((e) {
              return ListTile(
                title: Text("From ${e['start']} to ${e['end']}"),
                subtitle: Text("Duration: ${e['duration_minutes']} mins"),
              );
            }).toList(),
          );
        },
      ),
    );
  }
}
