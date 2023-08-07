# Fiat-Shamir Zero Knowledge Proof (ZKP) Algorithm


## Introduction

I've always been fascinated by cryptography and privacy in computing. My journey began with an understanding of Pretty Good Privacy (PGP), where I delved into data signing and verification processes. With the rise of blockchain technologies and secure communications, my interest in understanding how Zero Knowledge Proof (ZKP) algorithms work was piqued. As I began to dive into online resources, it became clear that implementing such an algorithm would be an exciting and educational project..

I wanted my implementation to be as close to reality as possible, mirroring real-world scenarios where two separate participants, the Prover and the Verifier, interact across different servers. Additionally, the separation of participants provided me with an opportunity to develop the solution with two different programming languages, providing a more complex and realistic setup.


## Technology Choices

### RabbitMQ

For the messaging system between the Prover and Verifier, I chose RabbitMQ. This decision is based on its ease of use and quick implementation. It enabled seamless communication between two distinct servers, aligning perfectly with my goal of simulating a real-world application.

However, it's important to note that, when the entire application stack is first initiated, the Prover and Verifier might not immediately have access to RabbitMQ due to the time it takes for the RabbitMQ server to become fully operational. To manage this, I have implemented a mechanism in both the Prover and Verifier scripts which attempts to establish a connection to RabbitMQ multiple times over a set duration. This ensures that the Prover and Verifier will start processing only once the connection to RabbitMQ is successfully established.


### Programming Languages

The use of two different programming languages for the Prover and Verifier components added an extra layer of realism and provided a challenging and rewarding coding experience.

* The Prover component is implemented in Python.
* The Verifier component is written in PHP.


## Algorithm Implementation

In implementing the Fiat-Shamir Zero Knowledge Proof algorithm, I adhered closely to the original specification, with a few necessary adaptations to accommodate the messaging system. Specifically, values that need to be communicated between the Prover and the Verifier, such as _'n'_ and _'v'_, are sent as messages through RabbitMQ queues. This adaptation improves the overall simulation, providing a more accurate representation of how such a system would operate in real-world scenarios.

To keep the simulation more manageable and the outputs easier to interpret, I've chosen a specific range for the generation of prime numbers _'p'_ and _'q'_, which are used to compute _'n'_. In a real-world application, these numbers would be significantly larger to ensure robust security. As explained in the [Wikipedia article on the Feige-Fiat-Shamir identification scheme](https://en.wikipedia.org/wiki/Feige%E2%80%93Fiat%E2%80%93Shamir_identification_scheme), _'n'_ should be the product of two large prime numbers, _'s'_ and _'r'_ should be less than _'n'_, and _'s'_ should be coprime to _'n'_. These conditions contribute to the security of the Fiat-Shamir protocol.

The system performs a number of iterations defined by the TOTAL_TESTS environment variable in the .env file, with a default of 20 if not specified. This setup allows for flexibility in the number of iterations, which can be adjusted to meet specific security requirements. In practice, this number can be changed as needed. Based on my research, a minimum of 20 iterations should be sufficient to verify whether the Prover truly knows the secret.

I have taken care to heavily comment the code to aid understanding for the reader (and for myself! :smiley:). This approach will facilitate a more in-depth comprehension of the algorithm's functioning and the design choices made.


## The Fiat-Shamir Zero Knowledge Proof algorithm explained

The Fiat-Shamir algorithm is a method for implementing a Zero-Knowledge Proof (ZKP) protocol. A ZKP is a method by which one party (the prover) can prove to another party (the verifier) that they know a value of a certain parameter, without conveying any information apart from the fact that they know the value.

Here's a simplified explanation of the algorithm:

**Setup Phase**: This is the initial stage before the message exchange begins. In this phase:
- The Prover possesses a secret _'s'_ that they aim to prove knowledge of to the Verifier, without revealing the secret itself.
- _'n'_ is a composite number which is the product of two prime numbers. Both the Prover and Verifier are aware of _'n'_.
- _'v'_ is a value calculated by the Prover as _v = (s * s) mod n_, which is then shared with the Verifier.

**Commitment Phase**: The prover begins by choosing a secret value _'s'_ and computes _v = (s * s) mod n_, where _'n'_ is a composite number (preferably a product of two large primes _'p'_ and _'q'_). The value _'v'_ is sent to the verifier. The prover also chooses a random number _'r'_ and computes _x = (r * r) mod n_. This value _'x'_ is the commitment and is sent to the verifier.

![Commitment Phase](https://oscarpascual.com/commitment-phase.png)

**Challenge Phase**: The verifier then sends a random challenge bit _'b'_ to the prover. This bit is either 0 or 1.

![Challenge Phase](https://oscarpascual.com/challenge-phase.png)

**Response Phase**: If the bit _'b'_ is 0, the prover sends _'r'_ back (since anything raised to the power of 0 is 1, and _'r'_ is less than _'n'_, the product of _'r'_ and 1 remains _'r'_ itself). If _'b'_ is 1, the prover sends _y = (r * s^b) mod n_ back.

![Response Phase](https://oscarpascual.com/response-phase.png)

**Verification Phase**: The verifier checks if _y * y mod n_ is equal to _'x'_ (if _'b'_ was 0) or to _x * v^b mod n_ (if _'b'_ was 1). If the check passes, the verifier can be assured that the prover knows the secret _s_.

![Verification Phase](https://oscarpascual.com/verification-phase.png)

This algorithm is iterated several times to reduce the probability of a malicious prover successfully passing the verification without knowing the secret.


## Installation and Running

This project is containerized using Docker, making it easy to build and run regardless of your development environment.

To install and run the Prover and Verifier:

1. Clone this repository:
```
git clone https://github.com/oscarpascualbakker/fiat-shamir-zero-knowledge-proof .
```

2. From the root directory of the project, build and run the Docker images using docker-compose:
```
docker-compose up -d
```

The Prover and Verifier services will start up immediately and begin interacting.

To review the results, you can check the logs of both the Prover and Verifier containers. This can be done with Docker's log command:

```
docker logs <container_id>
```

Where <container_id> is the ID of the container for which you want to view the logs.


## Expected Output

When you run the application, you should see outputs similar to the following:

**Prover Output:**

![Prover Output](https://oscarpascual.com/output-prover.png)

**Verifier Output:**

![Verifier Output](https://oscarpascual.com/output-verifier.png)

Please note that your actual output may vary due to the random nature of the Fiat-Shamir algorithm.


## References

1. **Fiat-Shamir Heuristic**: The Wikipedia page offering a detailed explanation of the heuristic algorithm.
   - [Wikipedia: Fiat-Shamir Heuristic](https://en.wikipedia.org/wiki/Fiat%E2%80%93Shamir_heuristic)

2. **Feige-Fiat-Shamir Identification Scheme**: The Wikipedia page offering a detailed explanation of the scheme.
   - [Wikipedia: Feige-Fiat-Shamir Identification Scheme](https://en.wikipedia.org/wiki/Feige%E2%80%93Fiat%E2%80%93Shamir_identification_scheme)

3. **Zero-Knowledge Proofs**: A comprehensive guide to Zero-Knowledge Proofs (ZKP).
   - [Wikipedia: Zero-Knowledge Proof](https://en.wikipedia.org/wiki/Zero-knowledge_proof)


## Conclusion

This project provided me with an invaluable opportunity to deepen my understanding of Zero Knowledge Proofs and cryptography in general. By attempting to align the implementation closely with real-world conditions, including the use of distinct servers (Docker containers in practice) and programming languages, as well as a robust messaging system, I feel that I have achieved a realistic and functional simulation of the Fiat-Shamir algorithm.

Please don't hesitate to share your thoughts or suggestions.