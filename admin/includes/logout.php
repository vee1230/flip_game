<?php
/**
 * logout.php — Admin panel logout: destroys admin session.
 */
session_start();
$_SESSION = [];
session_destroy();
header("Location: ../pages/index.php");
exit;
?>
