# Import libraries
# Pika is a pure-Python implementation of the AMQP 0-9-1 protocol.
# Random is a Python built-in library for generating pseudo-random numbers.
# Time provides various time-related functions. In this code, it is used to introduce a delay between connection attempts to RabbitMQ.
# Json provides methods to manipulate JSON data. In this code, it is used to convert a tuple of strings into a JSON string.
# Os provides the getenv function.
# Sympy is a Python library for symbolic mathematics. It provides the 'randprime()' function, which generates a random prime number in a given range. In this code, 'randprime()' is used to generate two random prime numbers.
# Decouple is a Python library to fetch environment variables and provide default fallbacks.
import pika
import random
import time
import json
import os
from sympy import randprime
from decouple import config

# Ensure the Prover has access to RabbitMQ.  This mechanism attempts to establish a
# connection to RabbitMQ multiple times over a set duration.
max_attempts = 10
attempts = 0
wait_time = 5

RABBITMQ_USER = config('RABBITMQ_USER', default='default_user')
RABBITMQ_PASS = config('RABBITMQ_PASS', default='default_pass')
while attempts < max_attempts:
    try:
        # Establish a connection to RabbitMQ server. The connection is blocking which means
        # that the network operations are on hold until they complete or timeout.
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host='rabbitmq',
                credentials=pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS),
                blocked_connection_timeout=300
            )
        )
        # If connection is established, break the loop.
        break

    except Exception as e:
        print(f"Attempt {attempts+1} failed. Retrying...", flush=True)
        attempts += 1
        time.sleep(wait_time)

if attempts == max_attempts:
    print("Max attempts reached. Could not establish a connection.", flush=True)
    exit()

# Open a new channel with RabbitMQ.
channel = connection.channel()

# Define queue names
QUEUE_INIT = config('QUEUE_INIT', default='init')
QUEUE_COMMITMENT = config('QUEUE_COMMITMENT', default='commitment')
QUEUE_CHALLENGE = config('QUEUE_CHALLENGE', default='challenge')
QUEUE_RESPONSE = config('QUEUE_RESPONSE', default='response')

# Declare the queues
channel.queue_declare(queue=QUEUE_INIT)
channel.queue_declare(queue=QUEUE_COMMITMENT)
channel.queue_declare(queue=QUEUE_CHALLENGE)
channel.queue_declare(queue=QUEUE_RESPONSE)


# Define a range for the prime numbers
lower_bound = 10000
upper_bound = 100000

# Generate two random prime numbers 'p' and 'q' within the defined range
p = randprime(lower_bound, upper_bound)
q = randprime(lower_bound, upper_bound)

# Calculate 'n' as product of 'p' and 'q'
n = p * q

# Generate random number 's' in the range of 2 and n-1
s = random.randint(2, n-1)

# Calculate 'v'
v = (s * s) % n

# Convert 'n' and 'v' to string and convert to json
n_str = str(n)
v_str = str(v)
nv_json_str = json.dumps((n_str, v_str))


# Send 'n' and 'v' to the Verifier through queue 'init'
print(f"Sending 'n': {n} and 'v': {v} to Verifier\n", flush=True)
channel.basic_publish(exchange='', routing_key=QUEUE_INIT, body=nv_json_str)


# This closure creates and returns another function - 'callback', that has access to the argument 'r'.
def make_callback(r):
    def callback(ch, method, properties, body):
        # This inner function (callback) computes and sends the response 'y',
        # which is based on the received challenge 'b' and the value 'r'.
        try:
            b = int(body)
            if not (0 <= b <= 1):
                raise ValueError("[ERROR] Invalid challenge value!")
        except ValueError:
            print("Received invalid challenge from the queue!")
            return

        y = (r * s ** b) % n
        print(f"  Received challenge: {b}.  Sending response: {y}", flush=True)
        channel.basic_publish(exchange='', routing_key=QUEUE_RESPONSE, body=str(y))
        channel.basic_cancel(consumer_tag=QUEUE_CHALLENGE)
    return callback

# This function is used as the callback for the 'challenge' queue. It creates a callback function using
# the current 'r' value.  Without this function 'r' is not consistent inside the callback.
def process_message(ch, method, properties, body):
    global current_r, challenge_received
    callback = make_callback(current_r)
    callback(ch, method, properties, body)
    challenge_received = True

# Tell RabbitMQ that this function should receive messages from the 'challenge' queue.
channel.basic_consume(queue=QUEUE_CHALLENGE, on_message_callback=process_message, auto_ack=True)

# Specify total number of iterations of the protocol (configured in .env). Fallback to '20' if not set
totalTests = int(os.getenv('TOTAL_TESTS') or '20')

# The main loop for the Prover side of the Fiat-Shamir protocol.
for i in range(totalTests):
    print(f"Iteration: {i+1}", flush=True)

    challenge_received = False

    # A random integer 'r' is generated for each iteration.
    current_r = random.randint(1, n-1)

    # When working with modular arithmetic, especially with large numbers as in cryptographic applications,
    # it's crucial to ensure that intermediate computations also respect the modulus. Without this, even though
    # Python supports arbitrary precision integers, we can encounter negative numbers due to the way modular
    # arithmetic is defined. By ensuring that intermediate calculations are also taken modulo 'n', we avoid
    # potential issues where the left-hand side of the modulo operation might be negative.
    #
    # For example, in the expression (a * b) % n, if a * b exceeds the maximum positive value an integer can
    # represent before wrapping around to a negative value, then the result of the modulo operation can also be
    # negative. By computing modulo `n` at each step, such as ((a % n) * (b % n)) % n, we ensure that our
    # computations remain positive and within expected bounds.
    #
    # So, instead of doing 'x = (current_r * current_r) % n' we do ...
    x = ((current_r % n) * (current_r % n)) % n

    # The computed commitment 'x' is sent to the 'commitment' queue.
    print(f"  Generated r: {current_r}, x: {x}. Sending commitment {x}...", flush=True)
    channel.basic_publish(exchange='', routing_key=QUEUE_COMMITMENT, body=str(x))

    # Process data events to handle incoming messages.
    while not challenge_received:
        channel._process_data_events(time_limit=3)

print("\nAll iterations completed.", flush=True)
