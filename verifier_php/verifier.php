<?php

// Import the required libraries for handling the AMQP protocol
use PhpAmqpLib\Connection\AMQPStreamConnection;
use PhpAmqpLib\Message\AMQPMessage;

require_once __DIR__ . '/vendor/autoload.php';

// Ensure the Prover has access to RabbitMQ.  This mechanism attempts to establish a
// connection to RabbitMQ multiple times over a set duration.
$max_attempts = 10;
$attempts = 0;
$wait_time = 5; // time in seconds

while($attempts < $max_attempts) {
    try {
        $connection = new AMQPStreamConnection('rabbitmq', 5672, 'test', 'test');
        // If connection is established, break the loop.
        break;
    } catch (Exception $e) {
        echo "Attempt " . ($attempts + 1) . " failed. Retrying...\n";
        $attempts++;
        sleep($wait_time); // Sleep for 5 seconds before the next attempt
    }
}

if ($attempts == $max_attempts) {
    echo "Max attempts reached. Could not establish a connection.\n";
    exit;
}


// Specify total number of iterations of the protocol
$passedTests = 0;
$totalTests = 20;

// Hardcode the values of 'n' and 'v' for simplicity
$n = 235;
$v = 89;

// Create a new channel within this connection
$channel = $connection->channel();

// Declare queues for commitment, challenge, and response
$channel->queue_declare('commitment', false, false, false, false);
$channel->queue_declare('challenge', false, false, false, false);
$channel->queue_declare('response', false, false, false, false);

// Define callback function for receiving commitment messages
$callbackCommitment = function ($msg) use (&$x) {
    $x = (int) $msg->body;
    echo '  [x] Received commitment ', $x, "\n";
};

// Define callback function for receiving response messages
$callbackResponse = function ($msg) use (&$x, &$y, &$b, &$passedTests) {
    global $v, $n;

    $y = (int) $msg->body;
    echo '  [x] Received response ', $y, "\n";

    // Calculate check value (y^2 mod n)
    $check = ($y * $y) % $n;

    if ($b == 1) {
        // Only if b=1, check must be done like this: y^2 mod n == x·v^b mod n and therefore, x must be adapted
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

// Start 20 iterations of the protocol
for ($i = 0; $i < $totalTests; $i++) {
    echo "Iteration: ", $i+1, "\n";

    $x = null;
    $y = null;

    // Step 1: Consume the commitment message
    $channel->basic_consume('commitment', '', false, true, false, false, $callbackCommitment);
    while ($x === null) {
        $channel->wait();
    }
    $channel->basic_cancel('commitment');

    // Step 2: Send the challenge message
    $b = rand(0, 1);
    $msg = new AMQPMessage((string) $b);
    $channel->basic_publish($msg, '', 'challenge');
    echo '  [x] Sent challenge ', $b, "\n";

    // Step 3: Consume the response message
    $channel->basic_consume('response', '', false, true, false, false, $callbackResponse);
    while (!isset($y)) {
        $channel->wait();
    }
    $channel->basic_cancel('response');
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