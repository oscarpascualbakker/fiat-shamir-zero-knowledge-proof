<?php

// Import the required libraries for handling the AMQP protocol
use PhpAmqpLib\Connection\AMQPStreamConnection;
use PhpAmqpLib\Message\AMQPMessage;
use Symfony\Component\Dotenv\Dotenv;

require_once __DIR__ . '/vendor/autoload.php';

$dotenv = new Dotenv();
$dotenv->load(__DIR__.'/.env');

// Ensure the Prover has access to RabbitMQ.  This mechanism attempts to establish a
// connection to RabbitMQ multiple times over a set duration.
$max_attempts = 10;
$attempts = 0;
$wait_time = 5; // time in seconds

$rabbitmq_host = $_ENV['RABBITMQ_HOST'] ?: 'rabbitmq';
$rabbitmq_port = intval($_ENV['RABBITMQ_PORT']) ?: 5672;
$rabbitmq_user = $_ENV['RABBITMQ_USER'] ?: 'default_user';
$rabbitmq_pass = $_ENV['RABBITMQ_PASS'] ?: 'default_pass';

$queue_init = $_ENV['QUEUE_INIT'] ?: 'init';
$queue_commitment = $_ENV['QUEUE_COMMITMENT'] ?: 'commitment';
$queue_challenge = $_ENV['QUEUE_CHALLENGE'] ?: 'challenge';
$queue_response = $_ENV['QUEUE_RESPONSE'] ?: 'response';


while($attempts < $max_attempts) {
    try {
        $connection = new AMQPStreamConnection($rabbitmq_host, $rabbitmq_port, $rabbitmq_user, $rabbitmq_pass);
        // If connection is established, break the loop.
        break;
    } catch (Exception $e) {
        echo "Attempt " . ($attempts + 1) . " failed. Retrying...\n";
        $attempts++;
        sleep($wait_time); // Sleep 'wait_time' seconds before the next attempt
    }
}

if ($attempts == $max_attempts) {
    echo "Max attempts reached. Could not establish a connection.\n";
    exit;
}

// Create a new channel within this connection
$channel = $connection->channel();

// Declare queues for init, commitment, challenge and response
$channel->queue_declare($queue_init, false, false, false, false);
$channel->queue_declare($queue_commitment, false, false, false, false);
$channel->queue_declare($queue_challenge, false, false, false, false);
$channel->queue_declare($queue_response, false, false, false, false);

function validate_data($data) {
    if (!is_numeric($data)) {
        throw new Exception("Data is not valid. Expected a number.");
    }
}

// Define callback for receiving 'n' and 'v' values
$n = null;
$v = null;
$callbackInit = function ($msg) use (&$n, &$v) {
    $nv = json_decode($msg->body);
    $n = $nv[0];
    $v = $nv[1];
    echo 'Received n: ', $n, ' and v: ', $v, "\n\n";
};

// Define callback function for receiving commitment messages
$callbackCommitment = function ($msg) use (&$x) {
    validate_data($msg->body);  // Punto 1.2: Validación de datos
    $x = (int) $msg->body;
    echo '  [x] Received commitment ', $x, "\n";
};

// Define callback function for receiving response messages
$callbackResponse = function ($msg) use (&$x, &$y, &$b, &$passedTests) {
    global $v, $n;

    validate_data($msg->body);  // Punto 1.2: Validación de datos

    $y = (int) $msg->body;
    echo '  [x] Received response ', $y, "\n";

    // Calculate check value (y^2 mod n). This is done to verify the prover's response.
    $check = ($y * $y) % $n;

    if ($b == 1) {
        // Only if b=1, check must be done like this: y^2 mod n == x * v^b mod n and therefore, x must be adapted
        // Otherwise check is simply y^2 mod n == x
        $x = ($x * $v) % $n;
    }

    // Verify if the check value matches 'x'
    if ($check == $x) {
        $passedTests++;
        echo "  [x] Test is OK: (response: $y, x = check = $check)", "\n";
    } else {
        echo "  [x] Test is NOT OK: (response: $y, x: $x, check: $check)", "\n";
    }
};

// First, obtain 'n' and 'v' from the Prover
$channel->basic_consume($queue_init, '', false, true, false, false, $callbackInit);
while (!isset($n) || !isset($v)) {
    $channel->wait();
}
$channel->basic_cancel($queue_init);

// Specify total number of iterations of the protocol
$totalTests = intval($_ENV['TOTAL_TESTS']) ?: 20;
$passedTests = 0;

# The main loop for the Verifier side of the Fiat-Shamir protocol.
for ($i = 0; $i < $totalTests; $i++) {
    echo "Iteration: ", $i+1, "\n";

    $x = null;
    $y = null;

    // Step 1: Consume the commitment message
    $channel->basic_consume($queue_commitment, '', false, true, false, false, $callbackCommitment);
    while ($x === null) {
        $channel->wait();
    }
    $channel->basic_cancel($queue_commitment);

    // Step 2: Send the challenge message. The challenge 'b' is a random bit (0 or 1).
    $b = rand(0, 1);
    $msg = new AMQPMessage((string) $b);
    $channel->basic_publish($msg, '', $queue_challenge);
    echo '  [x] Sent challenge ', $b, "\n";

    // Step 3: Consume the response message
    $channel->basic_consume($queue_response, '', false, true, false, false, $callbackResponse);
    while (!isset($y)) {
        $channel->wait();
    }
    $channel->basic_cancel($queue_response);
}

// Show result of the tests
if ($passedTests == $totalTests) {
    echo "\nAll tests passed. The Prover is validated.\n";
} else {
    echo "\nWARNING: Some tests failed. The Prover could not be fully validated.\n";
}

// Close the channel and the connection
$channel->close();
$connection->close();
?>