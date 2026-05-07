<?php
/** Compatibility shim — redirects to reorganized dashboard location. */
session_start();
if (empty($_SESSION['admin_logged_in'])) {
    header("Location: pages/index.php");
    exit;
}
header("Location: pages/dashboard.php");
exit;
?>
