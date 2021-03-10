BrFAST (Browser Fingerprinting Attribute Selection Tool)
========================================================

<!-- Screenshot of BrFAST -->
![BrFAST](brfast.png "BrFAST")


<!-- TABLE OF CONTENTS -->
<details open="open">
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
      <ul>
        <li><a href="#built-with">Built With</a></li>
      </ul>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#roadmap">Roadmap</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
  </ol>
</details>



## About The Project

<!-- Description of the objective of this repository -->
This repository hosts BrFAST, our Browser Fingerprinting Attribute Selection
Tool that we developed to demonstrate our method of attribute selection named
FPSelect. You can read the
[related article](https://doi.org/10.1145/3427228.3427297) which is also
available on [arXiv](https://arxiv.org/abs/2010.06404) and
[HAL](https://hal.archives-ouvertes.fr/hal-02965948).

<!-- How this repository works -->
BrFAST takes the form of a web application that you can use to select the
attributes to implement in your browser fingerprinting probe.


### Built With

- [Modin](https://modin.readthedocs.io) for the fingerprint analysis.
- [Flask](https://flask.palletsprojects.com) for the web application.
- [Bootstrap](https://getbootstrap.com) for the web pages.
- [D3JS](https://d3js.org) for the graph visualization.



## Getting Started

### Prerequisites

The attribute selection tool is developed in
[Python3](https://www.python.org/downloads) for which you should have a version
installed on your system.


### Installation

1. Clone this repository.
   ```sh
   git clone [PATH]
   ```
2. Create a virtual environment (not mandatory but recommended).
   ```sh
   # The virtual environment is created in a directory named "venv"
   python3 -m venv venv
   ```
3. Enter the scope of the virtual environment.
   ```sh
   source venv/bin/activate
   ```
4. Install the dependencies.
   ```sh
   pip install -r requirements.txt
   ```



## Usage

For now, you can execute the simple example that is provided in the module
named `example_basic`. To do so, you can execute the following command:

```sh
python -m example_basic.main
```



## Architecture

Below, we describe the content of each module of this project.

### example_basic

`example_basic` contains an example of execution of the FPSelect algorithm.

- `main.py` is the executable script to run the simple example.
  * `MySensitivity` is a simple sensitivity function used for this example.
  * `MyCost` is a simple usability cost function used for this example.

### fpselect

`fpselect` contains the implementation of the FPSelect algorithm and the
interfaces.

- `algorithm.py` contains the `FPSelect` class that implements the FPSelect
  algorithm.
- `attribute.py` contains the `Attribute` interface that represents the
  attributes.
- `cost.py` contains the interfaces that represent the usability cost of an
  attribute set.
  * `Cost` is the representation of the usability cost.
  * `CostFunction` is the interface of the usability cost measure.
- `sensitivity.py` contains the `SensitivityFunction` interface for the
  sensitivity measure.

### gui

`gui` contains the design files of the graphical user interfaces used in BrFAST.
You can refer to the readme in this directory for more information.


## Roadmap

The attribute selection tool is under development on a private repository. This
one is a public mirror that will include the features when they are ready. The
features to come are listed below.

- [ ] Implementation of a sensitivity measure by the proportion of the users
  that share the most common fingerprints.
- [ ] Implementation of a usability cost measure that captures the size and
  the instability of the generated fingerprints.
- [ ] Implementation of the usual attribute selection methods that rely on the
  entropy and the conditional entropy.
- [ ] Inclusion of the resources necessary to use the publicly available
  fingerprint datasets of
  [FPStalker](https://github.com/Spirals-Team/FPStalker) and
  [Henning Tillmann](https://www.henning-tillmann.de/2013/10/browser-fingerprinting-93-der-nutzer-hinterlassen-eindeutige-spuren).
- [ ] Implementation of the visualization of the current state of the   
  exploration of the possibilities as a graph using the D3JS library.
- [ ] Implementation of the visualization of the information on the generated
  fingerprints given an attribute set, displaying their sensitivity, their
  usability cost, their unicity, their entropy, their stability, and a sample
  of the resulting fingerprints.
- [ ] Implementation of the replay of an execution trace.



## License

Distributed under the MIT License. See `LICENSE` for more information.



## Contact

[Nampoina Andriamilanto](https://tandriamil.fr) - tompo.andri [at] gmail [dot]
com
