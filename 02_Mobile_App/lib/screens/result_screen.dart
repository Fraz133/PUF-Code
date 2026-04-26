import 'package:flutter/material.dart';

class ResultScreen extends StatelessWidget {
  final Map<String, dynamic> result;

  const ResultScreen({super.key, required this.result});

  @override
  Widget build(BuildContext context) {
    final isAuthenticated = (result['authentication'] ?? '').toString().contains('PASSED');
    
    return Scaffold(
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const SizedBox(height: 20),

              // Back button
              Align(
                alignment: Alignment.centerLeft,
                child: IconButton(
                  onPressed: () => Navigator.pop(context),
                  icon: const Icon(Icons.arrow_back_ios, color: Colors.white),
                ),
              ),

              const SizedBox(height: 16),

              // Main Result Badge
              Center(
                child: Container(
                  padding: const EdgeInsets.all(24),
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: RadialGradient(
                      colors: isAuthenticated
                          ? [Colors.greenAccent.withValues(alpha: 0.3), Colors.transparent]
                          : [Colors.redAccent.withValues(alpha: 0.3), Colors.transparent],
                      radius: 0.8,
                    ),
                  ),
                  child: Icon(
                    isAuthenticated ? Icons.check_circle : Icons.cancel,
                    size: 80,
                    color: isAuthenticated ? Colors.greenAccent : Colors.redAccent,
                  ),
                ),
              ),

              const SizedBox(height: 16),

              Center(
                child: Text(
                  isAuthenticated ? 'AUTHENTICATED' : 'AUTHENTICATION FAILED',
                  style: TextStyle(
                    fontSize: 24,
                    fontWeight: FontWeight.w800,
                    color: isAuthenticated ? Colors.greenAccent : Colors.redAccent,
                    letterSpacing: 2,
                  ),
                ),
              ),

              const SizedBox(height: 8),

              Center(
                child: Text(
                  'Tag: ${result['tag_id'] ?? 'N/A'} | Time: ${result['matched_against_time_node'] ?? 'N/A'}s',
                  style: TextStyle(
                    fontSize: 14,
                    color: Colors.white.withValues(alpha: 0.6),
                  ),
                ),
              ),

              const SizedBox(height: 32),

              // Key 1: Binary
              _buildKeyCard(
                context: context,
                title: 'Key 1: Binary Key',
                icon: Icons.grid_on,
                keyData: result['key_1_binary'],
                color: const Color(0xFF00E5FF),
              ),

              const SizedBox(height: 16),

              // Key 2: M-ary
              _buildKeyCard(
                context: context,
                title: 'Key 2: M-ary Key',
                icon: Icons.hexagon_outlined,
                keyData: result['key_2_mary'],
                color: const Color(0xFF7C4DFF),
              ),

              const SizedBox(height: 16),

              // Key 3: PMF
              _buildKeyCard(
                context: context,
                title: 'Key 3: PMF Key',
                icon: Icons.show_chart,
                keyData: result['key_3_pmf'],
                color: const Color(0xFFFF9100),
              ),

              const SizedBox(height: 32),

              // Scan again button
              SizedBox(
                height: 50,
                child: OutlinedButton.icon(
                  onPressed: () => Navigator.pop(context),
                  icon: const Icon(Icons.refresh),
                  label: const Text(
                    'SCAN ANOTHER TAG',
                    style: TextStyle(letterSpacing: 1.5, fontWeight: FontWeight.w600),
                  ),
                  style: OutlinedButton.styleFrom(
                    side: BorderSide(color: Theme.of(context).colorScheme.primary),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildKeyCard({
    required BuildContext context,
    required String title,
    required IconData icon,
    required dynamic keyData,
    required Color color,
  }) {
    if (keyData == null) {
      return _buildCardShell(title: title, icon: icon, color: color, children: [
        const Text('No data', style: TextStyle(color: Colors.white54)),
      ]);
    }

    final data = keyData as Map<String, dynamic>;
    final resultStr = (data['result'] ?? '').toString();
    final passed = resultStr.contains('PASS');
    final score = data['overall_score'] ?? 'N/A';
    final threshold = data['threshold'] ?? 'N/A';

    return _buildCardShell(
      title: title,
      icon: icon,
      color: color,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  score.toString(),
                  style: TextStyle(
                    fontSize: 32,
                    fontWeight: FontWeight.w800,
                    color: passed ? Colors.greenAccent : Colors.redAccent,
                  ),
                ),
                Text(
                  'Threshold: $threshold',
                  style: TextStyle(
                    fontSize: 12,
                    color: Colors.white.withValues(alpha: 0.5),
                  ),
                ),
              ],
            ),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              decoration: BoxDecoration(
                color: passed
                    ? Colors.greenAccent.withValues(alpha: 0.15)
                    : Colors.redAccent.withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(20),
              ),
              child: Text(
                passed ? 'PASS' : 'FAIL',
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w700,
                  color: passed ? Colors.greenAccent : Colors.redAccent,
                ),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildCardShell({
    required String title,
    required IconData icon,
    required Color color,
    required List<Widget> children,
  }) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: const Color(0xFF1A1F36),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: color.withValues(alpha: 0.2),
          width: 1,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 20, color: color),
              const SizedBox(width: 8),
              Text(
                title,
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                  color: color,
                  letterSpacing: 0.5,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          ...children,
        ],
      ),
    );
  }
}
