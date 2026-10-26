<?php
// This fixture is copied into a disposable test container, never into the image.
if (isset($_GET['oom'])) {
    ini_set('memory_limit', '16M');
    str_repeat('x', 32 * 1024 * 1024);
    exit('Unexpected allocation success');
}

session_start();
$_SESSION['visits'] = isset($_SESSION['visits']) ? $_SESSION['visits'] + 1 : 1;
$visits = $_SESSION['visits'];
session_write_close();

$database = new PDO('sqlite::memory:');
$database->exec('CREATE TABLE smoke (value TEXT)');
$database->exec("INSERT INTO smoke VALUES ('ok')");

$upload = null;
if (isset($_FILES['file'])) {
    $file = $_FILES['file'];
    $upload = array(
        'error' => $file['error'],
        'uploaded' => is_uploaded_file($file['tmp_name']),
        'sha256' => hash_file('sha256', $file['tmp_name'])
    );
}

header('Content-Type: application/json');
echo json_encode(array(
    'version' => PHP_VERSION,
    'sapi' => PHP_SAPI,
    'extensions' => get_loaded_extensions(),
    'upload_progress' => ini_get('session.upload_progress.enabled'),
    'gc_probability' => ini_get('session.gc_probability'),
    'memory_limit' => ini_get('memory_limit'),
    'max_execution_time' => ini_get('max_execution_time'),
    'max_input_vars' => ini_get('max_input_vars'),
    'upload_max_filesize' => ini_get('upload_max_filesize'),
    'post_max_size' => ini_get('post_max_size'),
    'timezone' => ini_get('date.timezone'),
    'uid' => posix_geteuid(),
    'gid' => posix_getegid(),
    'https' => isset($_SERVER['HTTPS']) ? $_SERVER['HTTPS'] : '',
    'visits' => $visits,
    'database' => $database->query('SELECT value FROM smoke')->fetchColumn(),
    'upload' => $upload
));
