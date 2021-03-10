/**
 * JS script to generate the lattice visualization using D3.js.
 *
 * Thanks to Tom Roth for his tutorials about force directed graphs using D3.js.
 * https://tomroth.com.au/d3
 */

// ##### Automatic update of the svg element size according to its parent
// NOTE This is for the responsiveness of the svg element

// Function to put the size of the svg element as the same as its parent
function setGraphSVGContainerSize() {
  // Get the HTML elements
  var graphContainerSVG = document.getElementById('graph-container');
  var graphContainerSVGParent = graphContainerSVG.parentNode;

  // Put the width and the height of the parent
  // NOTE The computed width does not remove the margins, hence I removed them manually
  graphContainerSVG.setAttribute('width', parseInt(graphContainerSVGParent.clientWidth) - 32);
  graphContainerSVG.setAttribute('height', graphContainerSVGParent.clientHeight);
}

// Set the size of the svg element at the loading of the web page
setGraphSVGContainerSize();

// Also resize this element when the web page is resized
window.addEventListener('resize', setGraphSVGContainerSize);


// ##### Parameters
var sensitivityThreshold = 0.15;


// ##### Create the data
// The nodes
var nodesData =  [
  {'id': 1, 'nb_attributes': 0, 'sensitivity': 1.0, 'usability_cost': 0},
  {'id': 2, 'nb_attributes': 1, 'sensitivity': 0.3, 'usability_cost': 10},
  {'id': 3, 'nb_attributes': 1, 'sensitivity': 0.3, 'usability_cost': 15},
  {'id': 4, 'nb_attributes': 1, 'sensitivity': 0.25, 'usability_cost': 15},
  {'id': 5, 'nb_attributes': 2, 'sensitivity': 0.15, 'usability_cost': 20},
  {'id': 6, 'nb_attributes': 2, 'sensitivity': 0.25, 'usability_cost': 17},
  {'id': 7, 'nb_attributes': 2, 'sensitivity': 0.20, 'usability_cost': 25},
  {'id': 8, 'nb_attributes': 3, 'sensitivity': 0.05, 'usability_cost': 30},
];

// The links
var linksData = [
  // Empty node to the three single attributes
  {'source': 1, 'target': 2}, {'source': 1, 'target': 3},
  {'source': 1, 'target': 4},

  // Single attributes to the pairs of attributes
  {'source': 2, 'target': 5}, {'source': 2, 'target': 6},
  {'source': 3, 'target': 5}, {'source': 3, 'target': 7},
  {'source': 4, 'target': 6}, {'source': 4, 'target': 7},

  // The pairs of attributes to the complete set of attributes
  {'source': 5, 'target': 8}, {'source': 6, 'target': 8},
  {'source': 7, 'target': 8}
];


// ##### Generate the simulation initialized with the nodes

// Refer to the HTML element that stores the graph
var svg = d3.select('svg'),
  width = parseInt(svg.attr('width')),
  height = parseInt(svg.attr('height'));

// Add encompassing group for the zoom
var g = svg.append('g').attr('class', 'everything');

// Set the simulation up
var simulation = d3.forceSimulation().nodes(nodesData);

// Set the forces up
simulation.force('charge_force', d3.forceManyBody())
          .force('center_force', d3.forceCenter(width / 2, height / 2));

// Returns the colour of a node according to its sensitivity
function circleColour(node) {
	if (node.sensitivity <= sensitivityThreshold) return 'green';
	else return 'blue';
}

// Draw the circles of the nodes
var nodes = g.append('g')
  .attr('class', 'nodes')
  .selectAll('circle')
  .data(nodesData)
  .enter()
  .append('circle')
  .attr('r', 7)
  .attr('fill', circleColour);


// ##### Add the links to the simulation

// Add the link force and specifies the id to use for the nodes ('name' here)
var linkForce =  d3.forceLink(linksData)
                   .id(function(node) { return node.id; });

// Add this force to the simulation
simulation.force('links', linkForce);

// Draw the lines of the links
var link = g.append('g')
  .attr('class', 'links')
  .selectAll('line')
  .data(linksData)
  .enter()
  .append('line')
  .attr('stroke-width', 2)
  .attr('stroke-opacity', 0.7)
  .style('stroke', 'black');


// ##### Add a custom force that put female nodes over male nodes (this example)

// NOTE For now, it is commented, but we could use it latter for the lattice.

// The function that increases the y position of female nodes by 5
// function splittingForce() {
//   for (var i = 0; i < nodesData.length; ++i) {
//     var node = nodesData[i];
//     if (node.sex == 'F') node.y -= 5;
//   }
// }

// Add this force to the simulation
// simulation.force('splitting_force', splittingForce);


// ##### Specify the tick function

/**
* Update the nodes position on each tick of the simulation
*/
function tickActions() {
  // Update the nodes position on each tick
  nodes.attr('cx', function(d) { return d.x; })
       .attr('cy', function(d) { return d.y; })

  // Update the links position on each tick
  link.attr('x1', function(d) { return d.source.x; })
      .attr('y1', function(d) { return d.source.y; })
      .attr('x2', function(d) { return d.target.x; })
      .attr('y2', function(d) { return d.target.y; });
}

// Bind the function to the tick event of the simulation
simulation.on('tick', tickActions);


// ##### Add Zoom capabilities (optional)

// Create the zoom handler and link it to the svg element
var zoomHandler = d3.zoom().on('zoom', zoomActions);
zoomHandler(svg);

// Define the zoom actions
function zoomActions(event, d) {
  g.attr('transform', event.transform);
}


// ##### Add Drag-and-drop capabilities (optional)

// The function to execute on the start event of the drag API
function dragStart(event, d) {
  if (!event.active) simulation.alphaTarget(0.3).restart();
  d.fx = d.x;
  d.fy = d.y;
}

// The function to execute on the drag event of the drag API
function dragDrag(event, d) {
  d.fx = event.x;
  d.fy = event.y;
}

// The function to execute on the end event of the drag API
function dragEnd(event, d) {
  if (!event.active) simulation.alphaTarget(0);
  d.fx = null;
  d.fy = null;
}

// Create the drag handler
var dragHandler = d3.drag()
  .on('start', dragStart)
  .on('drag', dragDrag)
  .on('end', dragEnd);

// Apply the drag handler to the nodes
dragHandler(nodes);
