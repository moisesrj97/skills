# Test Desiderata

From Kent Beck, *Test Desiderata* (2019). How the properties are used is in [`SKILL.md`](SKILL.md).

## Properties

| Property | The test… | Missing when… |
|---|---|---|
| **Isolated** | gives the same result whatever runs before or after it | it fails alone or only in the full suite |
| **Composable** | covers one dimension of variation, so dimensions are tested separately and combined | N inputs × M outputs need N×M tests |
| **Deterministic** | gives the same result while nothing changes | it reads the clock, randomness, the network or ordering it doesn't control |
| **Fast** | runs in the time a red → green cycle allows | the loop waits for it |
| **Writable** | costs little to write next to the code it tests | each new case needs a page of setup |
| **Readable** | tells a reader what it checks and why | the expected value is a magic number with no source |
| **Behavioral** | fails when the behaviour under test changes | breaking the code leaves it green |
| **Structure-insensitive** | keeps passing when the structure changes and the behaviour doesn't | a refactor turns it red |
| **Automated** | runs with no human in the loop | it needs a click, a manual setup step or a person reading output |
| **Specific** | points at the cause when it fails | a failure means reading the code to learn what broke |
| **Predictive** | tells you, when it passes, that the code works in production | the suite is green and production is broken |
| **Inspiring** | makes its passing worth trusting | people re-check by hand after a green run |

## Trade-offs

A property is given up only to buy another. The usual trades:

- **Predictive ↔ fast, deterministic**: an integration test through real collaborators predicts production better and runs slower and less reliably than one with fakes.
- **Structure-insensitive ↔ specific**: a test at an outer interface survives refactors, and a failure in it points less precisely at the cause.
- **Writable ↔ specific**: one broad test is cheap to write, and its failure says little.
- **Composable ↔ predictive**: testing dimensions separately covers more combinations for less, and misses bugs that live only in a combination.

A test-double earns its place by buying fast, deterministic or isolated where the real collaborator can't give them; one that sells predictive and buys nothing is a finding.
