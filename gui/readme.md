BrFAST - Graphical User Interfaces
==================================

This directory is dedicated to the design of the graphical interfaces of BrFAST.


## Installation

1. Download and extract the latest version of
   [bootstrap](https://getbootstrap.com) and [D3.js](https://d3js.org).
2. Create the links to the files listed below in the `libraries` directory.
   * `bootstrap.bundle.min.js` and the associated `.map`.
   * `bootstrap.min.css` and the associated `.map`.
   * `d3.vX.min.js`.


## Architecture

- `attribute-set-properties` contains the graphical user interface of the page
  displaying the properties of the fingerprints that would be obtained
  considering a given attribute set. This includes their unicity, entropy,
  stability, and usability cost among others.
- `exploration-state` contains the graphical user interface displaying the
  current exploration state that includes the parameters used for the
  execution, the usability gain compared to the complete set of attributes, and
  the explored nodes in the lattice of the possibilities.
- `libraries` contains the links to the libraries used by the graphical user
  interfaces.


## Resources
- Thanks to Tom Roth for his tutorials on
  [D3.js force directed graphs](https://tomroth.com.au/fdg-basics).
