/**
 * JS script to generate the lattice visualization using D3.js.
 *
 * Thanks to Tom Roth for his tutorials about force directed graphs using D3.js.
 * https://tomroth.com.au/d3
 */

// ##### Variables and parameters used for the visualization

// The precision of the floating point numbers shown
const FLOAT_PRECISION = 3;

// The state of an attribute set
const ATTRIBUTE_SET_STATE = {
   EXPLORED: 1,    // Simply explored
   PRUNED: 2,      // Pruned by a pruning method
   SATISFYING: 3,  // Satisfying the sensitivity threshold
   EMPTY_NODE: 4   // The starting empty node
};

// The classes for the progress bars
const PROGRESS_BAR_CLASSES = ['info', 'success', 'warning', 'danger'];

// We limit the number of displayed nodes for performance reasons
const NODES_LIMIT = 50;

// The empty node
const EMPTY_NODE = {
 id: -1, attributes: [], cost_explanation: {}, sensitivity: 1.0,
 state: ATTRIBUTE_SET_STATE.EMPTY_NODE, usability_cost: 0.0, time: '0:00:00.00'
}

// The id of the next node to collect, the STEP (i.e., how many attribute sets
// are collected every x seconds), and the collect frequency (i.e., the time in
// milliseconds after which we collect the next attribute sets)
var nextNodeId = 0;
const STEP = 25;
const COLLECT_FREQUENCY = 2000;

// The origin of the website and the URL for the /get-trace GET request
const BRFAST_ORIGIN = window.location.origin;
const GET_TRACE_URL = BRFAST_ORIGIN + '/get-trace';
const ATTRIBUTE_SET_URL = BRFAST_ORIGIN + '/attribute-set';

// The nodes and links which are updated through time
var nodes = [], links = [];

// A dictionary mapping the attributes set (list of attributes) to their ids
var attributesToNodeId = {};
attributesToNodeId[EMPTY_NODE.attributes] = EMPTY_NODE.id;

// The attribute set composed of the candidate attributes (i.e., all of them)
var candidateAttributes, costDimensions = undefined, undefined;

// The best solution currently found
var bestSolution = undefined, lowestUsabilityCost = Infinity;



// ##### Automatic update of the svg element size according to its parent

/**
 * Put the size of the svg element as the same as its parent.
 * @note This is for the svg element to be responsive.
 */
function setGraphSVGContainerSize() {
  // Get the HTML elements
  const graphContainerSVG = document.getElementById('graph-container');
  const graphContainerSVGParent = graphContainerSVG.parentNode;

  // Put the width and the height of the parent
  // NOTE The computed width does not remove the margins, hence I removed them manually
  graphContainerSVG.setAttribute('width', parseInt(graphContainerSVGParent.clientWidth) - 32);
  graphContainerSVG.setAttribute('height', graphContainerSVGParent.clientHeight);
}

// Set the size of the svg element at the loading of the web page
setGraphSVGContainerSize();

// Also resize this element when the web page is resized
window.addEventListener('resize', setGraphSVGContainerSize);


// ##### Generate the simulation

// Refer to the HTML element that stores the graph
const svg = d3.select('svg'),
  width = parseInt(svg.attr('width')),
  height = parseInt(svg.attr('height'));

// Add encompassing group for the zoom
const g = svg.append('g').attr('class', 'everything');


// ##### Functions that manipulate the dynamic visualization

/**
 * Update the nodes and the links.
 * @param newNodes The new nodes to add to the visualization.
 */
function updateNodesAndLinks(newNodes) {
  // ##### Update the nodes and the links of the simulation

  // TODO Try to limit the number of nodes that are shown for performances
  // nodes = nodes.concat(newNodes).slice(0, NODES_LIMIT);

  // Update the nodes
  nodes = nodes.concat(newNodes);

  // TODO Try to limit the number of nodes that are shown for performances
  // Object.entries(attributesToNodeId).slice(0, NODES_LIMIT).map(entry => entry[1]);

  // Infer the new links from the new nodes and the ones that are already drawn
  const newLinks = inferNewLinks(newNodes);

  // TODO Try to limit the number of nodes that are shown for performances
  // links = removeMissingLinks(links.concat(newLinks), nodes);

  // Update the links
  links = links.concat(newLinks);

  // Remove the previous nodes and links to avoid the ugly shadowing effect
  g.selectAll('.nodes').remove();
  g.selectAll('.links').remove();

  // Draw the lines of the links first for them to be below the nodes
  const link = g.append('g')
    .attr('class', 'links')
    .selectAll('line')
    .data(links)
    .enter()
    .append('line')
    .lower()
    .attr('stroke-width', 2)
    .attr('stroke-opacity', 0.7)
    .style('stroke', 'grey');

  // Draw the circles of the nodes
  const node = g.append('g')
    .attr('class', 'nodes')
    .selectAll('circle')
    .data(nodes)
    .enter()
    .append('circle')
    .attr('r', 7)
    .attr('fill', circleColour)
    .on('click', nodeClickAction)
    .on('mouseenter', nodeMouseEnterAction)
    .on('mouseleave', nodeMouseLeaveAction);

  // Set the simulation up
  const simulation = d3.forceSimulation();

  // Set the nodes in the simulation
  simulation.nodes(nodes);

  // Set the forces up
  const linkForce =  d3.forceLink(links).id(function(node) { return node.id; });
  simulation.force('charge_force', d3.forceManyBody())
            .force('center_force', d3.forceCenter(width / 2, height / 2))
            .force('collision', d3.forceCollide(function(node) {
              return node.radius*2;
            }))
            .force('links', linkForce);


  // ##### Specify the tick function

  /**
  * Update the nodes position on each tick of the simulation.
  */
  function tickActions() {
    // Update the nodes position on each tick
    node.attr('cx', function(d) { return d.x; })
        .attr('cy', function(d) { return d.y; });

    // Update the links position on each tick
    link.attr('x1', function(d) { return d.source.x; })
        .attr('y1', function(d) { return d.source.y; })
        .attr('x2', function(d) { return d.target.x; })
        .attr('y2', function(d) { return d.target.y; });
  }

  // Bind the function to the tick event of the simulation
  simulation.on('tick', tickActions);


  // ##### Add Zoom capabilities (optional)

  /**
   * The zoom action function.
   */
  function zoomActions(event, d) {
    g.attr('transform', event.transform);
  }

  // Create the zoom handler and link it to the svg element
  const zoomHandler = d3.zoom().on('zoom', zoomActions);
  zoomHandler(svg);


  // ##### Add Drag-and-drop capabilities (optional)

  /**
   * Execute the start event of the drag API.
   */
  function dragStart(event, d) {
    if (!event.active) simulation.alphaTarget(0.3).restart();
    d.fx = d.x;
    d.fy = d.y;
  }

  /**
   * Execute the drag event of the drag API.
   */
  function dragDrag(event, d) {
    d.fx = event.x;
    d.fy = event.y;
  }

  /**
   * Execute the end event of the drag API.
   */
  function dragEnd(event, d) {
    if (!event.active) simulation.alphaTarget(0);
    d.fx = null;
    d.fy = null;
  }

  // Create the drag handler
  const dragHandler = d3.drag()
    .on('start', dragStart)
    .on('drag', dragDrag)
    .on('end', dragEnd);

  // Apply the drag handler to the nodes
  dragHandler(node);

  // Restart the simulation (I don't know what this function really does)
  // simulation.alpha(1).restart();
}


/**
 * The action triggered on the click event on the nodes. It opens a new tab
 * to the page displaying the information about an attribute set.
 * @note The variable this refers to the node that was clicked.
 */
function nodeClickAction() {
  const attributeInformationUrl = ATTRIBUTE_SET_URL + '/' + $(this)[0].__data__.id;
  window.open(attributeInformationUrl, '_blank');
}


/**
 * The action triggered on the mouseenter event on the nodes. It shows the
 * information about the node.
 */
function nodeMouseEnterAction() {
  // We dispose of all the existing popovers to fix the bug of shadowing popover
  // that occurs when the user passes the mouse over the nodes during their
  // update. The selected node could move out of the reach of the mouse and
  // the popover then remains. Find a better solution if there is one.
  $('.popover').popover('dispose');

  const nodeData = $(this)[0].__data__;

  console.log(nodeData);

  // Compute the state
  let stateInformation = '';
  if (nodeData.state == ATTRIBUTE_SET_STATE.EXPLORED) {
    stateInformation = 'explored';
  } else if (nodeData.state == ATTRIBUTE_SET_STATE.PRUNED) {
    stateInformation = 'pruned';
  } else if (nodeData.state == ATTRIBUTE_SET_STATE.SATISFYING) {
    stateInformation = 'satisfying the threshold';
  } else if (nodeData.state == ATTRIBUTE_SET_STATE.EMPTY_NODE) {
    stateInformation = 'starting empty node';
  } else {
    stateInformation = 'unknown';
  }

  // Create the content of the popover
  let popoverContent = '';
  popoverContent += 'State: ' + stateInformation + '<br/>';
  popoverContent += 'Sensitivity: ' + nodeData.sensitivity.toFixed(FLOAT_PRECISION) + '<br/>';
  popoverContent += 'Usability cost: ' + nodeData.usability_cost.toFixed(FLOAT_PRECISION) + '<br/>';

  // For each cost dimension
  let j = costDimensions.length;
  while (j--) {
    const costDimension = costDimensions[j];
    if (!costDimension.startsWith('weighted')) {
      const costDimensionValue = nodeData.cost_explanation[costDimension];
      const costDimUppercase = costDimension.charAt(0).toUpperCase() + costDimension.slice(1);

      popoverContent += costDimUppercase + ' cost: ' + costDimensionValue.toFixed(FLOAT_PRECISION) + '<br/>';
    }
  }

  popoverContent += 'Time: ' + nodeData.time + '<br/>';

  // Put and show the popover
  $(this).popover({
      title: 'Id ' + nodeData.id + ' (' + nodeData.attributes.length + ' attributes)',
      content: popoverContent,
      html: true
  }).popover('show');
}


/**
 * The action triggered on the mouseleave event on the nodes. It hides the
 * information about the node.
 */
function nodeMouseLeaveAction() {
  $(this).popover('dispose');
}


/**
 * Give the colour of a node according to its state.
 * @param node The node for which to compute the colour.
 * @return The colour of the node.
 */
function circleColour(node) {
  switch (node.state) {
    case ATTRIBUTE_SET_STATE.EXPLORED:  // Explored
      return 'blue';

    case ATTRIBUTE_SET_STATE.PRUNED:  // Pruned
      return 'orange';

    case ATTRIBUTE_SET_STATE.SATISFYING:  // Satisfying the sensitivity
      // The best solution is in red
      if (bestSolution && node.id == bestSolution.id)
        return 'red';
      return 'green';

    case ATTRIBUTE_SET_STATE.EMPTY_NODE:  // The empty node
      return 'cyan';

    default:  // Otherwise, just colour as explored
      console.warn('Unknown node state: ' + node.state);
      return 'blue';
  }
}


// ##### Dynamically get the nodes from the BrFAST webserver

/**
 * Infer new links for the new nodes according to the ones that are already in
 * the visualization.
 * @param newNodes The new nodes for which to infer the new links.
 * @return The new links to add to the current links.
 */
function inferNewLinks(newNodes) {
  const newLinks = [];

  let j = newNodes.length;
  while (j--) {
    const newNode = newNodes[j];
    const attributes = newNode.attributes;

    // If the attribute set is composed of a single attribute, link it to the
    // empty set
    if (attributes.length == 1) {
      newLinks.push({source: EMPTY_NODE, target: newNode.id});
    } else {

      // Otherwise, compute all of its subsets (the attribute ids are sorted)
      let i = attributes.length;
      while(i--) {
        const below_i = attributes.slice(0, i);
        const above_i = attributes.slice(i+1, attributes.length);
        const attributes_subset = below_i.concat(above_i);

        // If the subset exists in the current nodes, find its id using the
        // attributesToNodeId dictionary, and link the new node to it
        if (attributes_subset in attributesToNodeId) {
          const subset_node_id = attributesToNodeId[attributes_subset];
          newLinks.push({source: subset_node_id, target: newNode.id});
        }
      }
    }
  }

  return newLinks;
}


/**
 * Remove the missing links as we remove the oldest links.
 * @param links The links from which to remove invalid links.
 * @param nodes The current nodes.
 * @return A new list of links with the invalid links removed.
 * @note Not used for now, to be updated when we implement the node limit.
 * @todo Update when we will try to limit the number of nodes drawn.
 */
function removeMissingLinks(links, nodes) {
  // Get the ids of the current nodes
  const nodesIds = [];
  let i = nodes.length;
  while (i--) {
    const node = nodes[i];
    nodesIds.push(node.id);
  }

  const cleanLinks = [];

  // Only hold the links for which the source and the target both exist
  i = links.length;
  while (i--) {
    const link = links[i];
    if (nodesIds.includes(link.source) && nodesIds.includes(link.target)) {
      console.log('Adding the link : (' + link.source + ', ' + link.target + ')');
      cleanLinks.push(link);
    } else {
      console.warn('Missing link : (' + link.source + ', ' + link.target + ')');
    }
  }

  return cleanLinks;
}


/**
 * Get the new nodes from the BrFAST server.
 */
function getAndUpdateNodes() {
  // Build and execute the GET request
  let xhr = new XMLHttpRequest();
  const url = GET_TRACE_URL + '/' + nextNodeId + '/' + (nextNodeId+STEP);
  console.log('Getting ' + url);
  xhr.open('GET', url, true); // true for asynchronous request

  xhr.onload = function (e) {
    if (xhr.readyState === 4) {
      if (xhr.status === 200) {
        if (xhr.responseText != '[]') {
          updateFromJsonResponse(xhr.responseText);
          nextNodeId = nextNodeId + STEP + 1;
          setTimeout(getAndUpdateNodes, COLLECT_FREQUENCY);
        }
      } else {
        console.error(xhr.statusText);
      }
    }
  };
  xhr.onerror = function (e) {
    console.error(xhr.statusText);
  };
  xhr.send(null);
}


/**
 * Update the nodes and links from a json response.
 * @param jsonResponse The json response.
 */
function updateFromJsonResponse(jsonResponse) {
  // Parse the response to generate the object containing the new nodes
  const newNodes = JSON.parse(jsonResponse);

  // For each new node, add it to the dictionary mapping the attributes to the
  // id of the attribute sets (which are the nodes)
  let i = newNodes.length;
  while (i--) {
    const newNode = newNodes[i];
    attributesToNodeId[newNode.attributes] = newNode.id;
  }

  // If the first set of new nodes, initialize the exploration state
  if (candidateAttributes === undefined) {
    initializeExplorationState(newNodes);
  }

  // Update the graphical elements on the web page
  updateExplorationState(newNodes);

  // Update the visual node and links
  updateNodesAndLinks(newNodes);
}


/**
 * Update the graphical elements on the web page showing the exploration state
 * with the best solution and the cost reduction.
 * @param newNodes The new nodes from which we will update the exploration
 *                 state.
 */
function updateExplorationState(newNodes) {
  // Check the best solution
  let newBestSolution = false;
  let i = newNodes.length;
  while (i--) {
    const currentNode = newNodes[i];

    // Only if satisfying node and lower sensitivity threshold
    if (currentNode.state == ATTRIBUTE_SET_STATE.SATISFYING && currentNode.usability_cost < lowestUsabilityCost) {
      bestSolution = currentNode;
      lowestUsabilityCost = currentNode.usability_cost;
      newBestSolution = true;
    }
  }

  // Update the best solution
  if (newBestSolution) {

    // Update the exploration state textual information
    $('#best-solution').text(bestSolution.id);
    $('#best-solution').attr('href', ATTRIBUTE_SET_URL + '/' + bestSolution.id);
    $('#best-solution').attr('target', '_blank');
    $('#best-sensitivity').text(bestSolution.sensitivity.toFixed(FLOAT_PRECISION));
    $('#best-usability-cost').text(lowestUsabilityCost.toFixed(FLOAT_PRECISION));

    // Update the progress bars
    const usabilityCostProportion = (100 * lowestUsabilityCost/candidateAttributes.usability_cost).toFixed(2);
    $('#progress-usability-cost').text(usabilityCostProportion + '%');
    $('#progress-usability-cost').attr('aria-valuenow', usabilityCostProportion);
    $('#progress-usability-cost').css('width', usabilityCostProportion + '%');

    // For each cost dimension
    let j = costDimensions.length;
    while (j--) {
      const costDimension = costDimensions[j];
      const costDimensionValue = bestSolution.cost_explanation[costDimension];
      if (!costDimension.startsWith('weighted')) {
        $('#best-cost-dimension-' + costDimension).text(costDimensionValue.toFixed(FLOAT_PRECISION));
        const costDimensionProportion = (100 * costDimensionValue / candidateAttributes.cost_explanation[costDimension]).toFixed(2);
        $('#cost-progress-bar-' + costDimension).text(costDimensionProportion + '%');
        $('#cost-progress-bar-' + costDimension).attr('aria-valuenow', costDimensionProportion);
        $('#cost-progress-bar-' + costDimension).css('width', costDimensionProportion + '%');
      }
    }
  }

  // Update the number of explored nodes
  $('#explored-nodes').text(nodes.length + newNodes.length);
}


/**
 * Initialize the exploration state with the first set of new nodes.
 * @param firstNewNodes The first set of the new nodes.
 */
function initializeExplorationState(firstNewNodes) {
  // The candidate attributes is the first node that is computed
  candidateAttributes = firstNewNodes[0];

  // Just assert that its id is really 0
  if (candidateAttributes.id != 0) {
    console.warn('The candidate attributes has a wrong ID: ' + candidateAttributes.id);
  }

  // From it, add the cost dimensions
  costDimensions = Object.getOwnPropertyNames(candidateAttributes.cost_explanation);
  let j = costDimensions.length;
  while (j--) {
    const costDimension = costDimensions[j];
    if (!costDimension.startsWith('weighted')) {
      $('#exploration-state-table').append('<tr><th scope="row">Best ' + costDimension + ' cost</th><td id="best-cost-dimension-' + costDimension + '">...</td></tr>');
      const progressBarClass = PROGRESS_BAR_CLASSES[j%PROGRESS_BAR_CLASSES.length];
      const costDimUppercase = costDimension.charAt(0).toUpperCase() + costDimension.slice(1);
      $('#usability-cost-progress-bars').append('<div>' + costDimUppercase + ' cost<div class="progress"><div class="progress-bar bg-' + progressBarClass + '" role="progressbar" style="width: 100%" aria-valuenow="100" aria-valuemin="0" aria-valuemax="100" id="cost-progress-bar-' + costDimension + '">100%</div></div></div>');

      // Also add this cost dimension to the empty node
      EMPTY_NODE.cost_explanation[costDimension] = 0.0;
    }
  }
}


// ##### Main execution of this script
// Update the current nodes by adding the empty node
updateNodesAndLinks([EMPTY_NODE]);

// Call the collect function at the beginning, which will call itself later
getAndUpdateNodes();
