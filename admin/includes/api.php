<?php
require_once '../../backend/config/config.php';

header('Content-Type: application/json');

$action = $_GET['action'] ?? '';

if (!$action) {
    echo json_encode(['error' => 'No action specified']);
    exit;
}

try {
    switch ($action) {
        case 'get_overview':
            $stmt = $pdo->query("SELECT COUNT(*) as total FROM players");
            $total_users = $stmt->fetch()['total'];
            $stmt = $pdo->query("SELECT COUNT(*) as total FROM scores");
            $total_games = $stmt->fetch()['total'];
            $stmt = $pdo->query("SELECT MAX(score) as max_score FROM scores");
            $max_score = $stmt->fetch()['max_score'];
            $stmt = $pdo->query("SELECT COUNT(*) as active FROM players WHERE status = 'Active'");
            $active_users = $stmt->fetch()['active'];
            $stmt = $pdo->query("SELECT COUNT(*) as total FROM players WHERE account_type = 'Guest'");
            $total_guests = $stmt->fetch()['total'];
            $stmt = $pdo->query("SELECT COUNT(*) as total FROM players WHERE account_type = 'Google'");
            $total_google = $stmt->fetch()['total'];
            echo json_encode([
                'total_users'  => $total_users,
                'total_games'  => $total_games,
                'max_score'    => $max_score,
                'active_users' => $active_users,
                'total_guests' => $total_guests,
                'total_google' => $total_google
            ]);
            break;

        case 'get_users':
            $stmt = $pdo->query("SELECT id, display_name, username, email, account_type, status, created_at FROM players ORDER BY created_at DESC");
            echo json_encode($stmt->fetchAll());
            break;

        case 'get_leaderboard':
            $stmt = $pdo->query("
                SELECT s.score, s.stage, s.theme, s.time_seconds, s.achieved_at, p.display_name, p.account_type
                FROM scores s
                JOIN players p ON s.player_id = p.id
                ORDER BY s.score DESC
                LIMIT 10
            ");
            echo json_encode($stmt->fetchAll());
            break;

        case 'get_activities':
            $stmt = $pdo->query("
                SELECT a.action_type, a.details, a.created_at, p.display_name
                FROM activities a
                JOIN players p ON a.player_id = p.id
                ORDER BY a.created_at DESC
                LIMIT 15
            ");
            echo json_encode($stmt->fetchAll());
            break;

        case 'get_analytics':
            $stmt = $pdo->query("SELECT stage, COUNT(*) as count FROM scores GROUP BY stage");
            $difficulties = $stmt->fetchAll();
            $stmt = $pdo->query("SELECT theme, COUNT(*) as count FROM scores GROUP BY theme");
            $themes = $stmt->fetchAll();
            echo json_encode(['difficulties' => $difficulties, 'themes' => $themes]);
            break;

        case 'update_user':
            $data         = json_decode(file_get_contents('php://input'), true);
            $id           = (int)($data['id'] ?? 0);
            $display_name = trim($data['display_name'] ?? '');
            $username     = trim($data['username'] ?? '');
            $email        = trim($data['email'] ?? '');
            $status       = in_array($data['status'] ?? '', ['Active', 'Inactive', 'Banned']) ? $data['status'] : 'Active';
            if (!$id || !$display_name || !$username) {
                echo json_encode(['error' => 'Missing required fields.']);
                break;
            }
            $stmt = $pdo->prepare("UPDATE players SET display_name=:dn, username=:un, email=:em, status=:st WHERE id=:id");
            $stmt->execute(['dn' => $display_name, 'un' => $username, 'em' => $email, 'st' => $status, 'id' => $id]);
            echo json_encode(['success' => true]);
            break;

        case 'delete_user':
            $data = json_decode(file_get_contents('php://input'), true);
            $id   = (int)($data['id'] ?? 0);
            if (!$id) { echo json_encode(['error' => 'Invalid ID.']); break; }
            $stmt = $pdo->prepare("DELETE FROM players WHERE id=:id");
            $stmt->execute(['id' => $id]);
            echo json_encode(['success' => true]);
            break;

        default:
            echo json_encode(['error' => 'Invalid action']);
    }
} catch (PDOException $e) {
    echo json_encode(['error' => $e->getMessage()]);
}
?>
