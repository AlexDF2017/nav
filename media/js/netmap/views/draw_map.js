define([
    'jquery',
    'underscore',
    'backbone',
    'backbone_eventbroker',
    'handlebars',
    'netmapextras',
    // Pull in the Collection module from above
    'views/netbox_info',
    'text!templates/draw_map.html'
], function ($, _, Backbone, BackboneEventbroker, Handlebars, NetmapExtras, NetboxInfoView, netmapTemplate ) {

    var drawNetmapView = Backbone.View.extend({
        tagName: "div",
        id: "chart",

        broker: Backbone.EventBroker,
        interests: {
            'map:resize:animate': 'resizeAnimate',
            'map:redraw': 'render'
        },
        initialize: function () {
            this.broker.register(this);

            this.model = this.options.context_selected_map.graph;

            this.$el.append(netmapTemplate);
            this.model.bind("change", this.render, this);
            this.model.bind("destroy", this.close, this);

            this.context_selected_map = this.options.context_selected_map;
            this.sidebar = this.options.view_netbox_info;

            this.w = this.options.cssWidth;
            this.h = screen.height - 500;
            this.trans = [0,0];
            this.scale = 1;
            this.zoom = d3.behavior.zoom();
            // swap .on with .bind for jQuery<1.7
            $(window).on("resize.app", _.bind(this.resize, this));
        },
        resizeAnimate: function (margin) {
            var self = this;

            var marginRight = margin.marginRight;
            var marginLeft = margin.marginLeft;

            // parent is $("#netmap_main_view"), required due to 3col collapse
            // layout. This breaks container principle, but it's django
            // who renders backbone.html template.
            this.$el.parent().animate({
                    'margin-right': "{0}px".format(marginRight),
                    'margin-left': "{0}px".format(marginLeft)
                },
                {   duration: 400,
                    step:     function () {
                        self.resize(self.$el.width() - 100);
                    },
                    complete: function () {
                        self.resize(self.$el.width());
                    }
                });
            //$("#netmap_main_view").animate({'margin-left': "{0}px".format(margin)}, 400);
        },
        resize: function (width) {
            if (!isNaN(width)) {
                this.w = width;
            } else {
                this.w = this.$el.width();
            }
            this.h = this.$el.height();

            (this.$el).find('#svg-netmap').attr('width', this.w);
            (this.$el).find('#svg-netmap').attr('height', this.h);
            (this.$el).find('#svg-netmap rect').attr('width', this.w);
            (this.$el).find('#svg-netmap rect').attr('height', this.h);

        },
        render: function () {

            var chart, svg, trans, scale, self;
            self = this;
            svg = self.svg;

            chart = this.$el[0],
                r = 6,
                fill = d3.scale.category20();



            self.zoom = d3.behavior.zoom();

            if (svg === undefined) {

                var root_chart = d3.select(this.el)
                    .append("svg:svg")
                    .attr('id', 'svg-netmap')
                    .attr("width", self.w)
                    .attr("height", self.h)
                    .attr("pointer-events", "all");
                root_chart
                    .append('svg:rect')
                    .attr('width', self.w)
                    .attr('height', self.h)
                    .attr('fill', 'white')
                    .call(self.zoom.on("zoom", redraw));
                svg = root_chart .append('svg:g')
                    //.call(d3.behavior.zoom().on("zoom", redraw))
                    .append('svg:g')
                ;
                this.svg = svg;
                console.log("Creating SVG vis");
            }


            function redraw() {
                self.trans=d3.event.translate;
                self.scale=d3.event.scale;
                svg.attr("transform",
                    "translate(" + self.trans + ") scale(" + self.scale + ")");
            }

            //json = {}
            function validateTranslateScaleValues() {
                if (isNaN(self.scale)) {
                    console.log("[Netmap][WARNING] Received invalid scale, use default scaling: {0}".format(self.scale));
                    self.scale = 1 / Math.log(json.nodes.length);
                }
                if (self.trans.length !== 2 || isNaN(self.trans[0]) || isNaN(self.trans[1])) {
                    console.log("[Netmap][WARNING] Received invalid translate values, centering graph: {0}".format(self.trans));
                    self.trans = [(-self.w/2)*(self.scale-1), (-self.h/2)*(self.scale-1)];
                }
            }

            var draw = function (data) {
                json = data;

                // translate and scale to saved settings
                if (!self.context_selected_map.map.isNew() && self.context_selected_map.map.attributes.zoom !== undefined) {
                    var tmp = self.context_selected_map.map.attributes.zoom.split(";");

                    self.trans = tmp[0].split(",");
                    self.scale = tmp[1];
                    validateTranslateScaleValues();
                    self.zoom.translate(self.trans);
                    self.zoom.scale(self.scale);

                    svg.attr("transform",
                        "translate(" + self.trans + ") scale(" + self.scale + ")");

                } else {
                    // adjust scale and translated according to how many nodes
                    // we're trying to draw

                    // Guess a good estimated scaling factor
                    self.scale = 1 / Math.log(json.nodes.length);

                    // translate ( -centerX*(factor-1) , -centerY*(factor-1) ) scale(factor)
                    // Example: SVG view pot 800x600, center is 400,300
                    // Reduce 30%, translate( -400*(0.7-1), -300*(0.7-1) ) scale(0.7)
                    self.trans = [(-self.w/2)*(self.scale-1), (-self.h/2)*(self.scale-1)];

                    validateTranslateScaleValues();
                    self.zoom.scale(self.scale);
                    self.zoom.translate(self.trans);

                    svg.attr("transform",
                        "translate(" + self.trans + ") scale(" + self.scale + ")");

                }

                //svg.attr("transform", "translate({0}) scale({1})".format(self.zoom.trans, self.zoom.scale));


                // FILTERS ON CATEGORIES ---- EXTRACT METHOD PLEASE
                // FILTERS ON CATEGORIES ---- EXTRACT METHOD PLEASE

                self.force = d3.layout.force().gravity(0.1).charge(-2500).linkDistance(250).size([self.w, self.h])
                    .nodes(json.nodes).links(json.links).on("tick", tick).start();

                //0-100, 100-512,512-2048,2048-4096,>4096 Mbit/s
                var s_link = svg.selectAll("g line").data(json.links);

                s_link.enter().append("svg:g").attr("class", "link").forEach(function (d,i) {

                    var gradient = s_link
                        .append("svg:linearGradient")
                        .attr("id", function(d,i) { return 'linkload'+i; })
                        .attr('x1', '0%')
                        .attr('y1', '0%')
                        .attr('x2', '0%')
                        .attr('y2', '100%');
                    gradient
                        .append("svg:stop")
                        .attr('offset', '0%')
                        .attr('style', function(d) {
                            if (d.data.traffic.inOctets_css) return 'stop-color:rgb('+d.data.traffic.inOctets_css+');stop-opacity:1'
                            else return 'stop-color:rgb(0,0,0);stop-opacity:1'
                        });
                    gradient
                        .append("svg:stop")
                        .attr('offset', '50%')
                        .attr('style', function(d) {
                            if (d.data.traffic.inOctets_css) return 'stop-color:rgb('+d.data.traffic.inOctets_css+');stop-opacity:1'
                            else return 'stop-color:rgb(0,0,0);stop-opacity:1'
                        });
                    gradient
                        .append("svg:stop")
                        .attr('offset', '51%')
                        .attr('style', function(d) {
                            if (d.data.traffic.outOctets_css) return 'stop-color:rgb('+d.data.traffic.outOctets_css+');stop-opacity:1'
                            else return 'stop-color:rgb(0,0,0);stop-opacity:1'

                        });
                    gradient
                        .append("svg:stop")
                        .attr('offset', '100%')
                        .attr('style', function(d) {
                            if (d.data.traffic.outOctets_css) return 'stop-color:rgb('+d.data.traffic.outOctets_css+');stop-opacity:1'
                            else return 'stop-color:rgb(0,0,0);stop-opacity:1'
                        });
                    s_link.append("svg:line")
                        .attr("class", function(d,i) {
                            var speed = d.data.link_speed;
                            var classes = "";
                            if(speed<=100){ classes = 'speed0-100' }
                            else if(speed>100 && speed<=512){ classes = 'speed100-512' }
                            else if(speed>512 && speed<=2048){ classes = 'speed512-2048' }
                            else if(speed>2048 && speed<=4096){ classes = 'speed2048-4096'}
                            else if(speed>4096){ classes = 'speed4096'}
                            else { classes = 'speedunknown'}
                            if (d.data.tip_inspect_link) { classes=classes+" warning_inspect"}
                            return classes;

                        })
                        .attr('stroke', function(d,i) { return 'url(#linkload'+i+')'})
                        .on("mouseover", function(d) { return link_popup(d) })
                        .on("mouseout", function(d) { return link_popout(d) });
                });

                var link = svg.selectAll("g.link line")

                var node_s = svg.selectAll("g circle").data(json.nodes);
                //var drag = d3.behavior.drag()
                //      .origin(Object)
                //.call(d3.behavior.zoom().on("zoom", redraw))
                var node_drag =
                    d3.behavior.drag()
                        .on("dragstart", dragstart)
                        .on("drag", dragmove)
                        .on("dragend", dragend);


                node_s.enter().append("svg:g")
                    .attr("class", "node")
                    .append("svg:image")
                    .attr("class", "circle node")
                    .attr("xlink:href", function (d) {
                        return "/images/netmap/"+ d.data.category.toLowerCase() + ".png";
                    })
                    .attr("x", "-16px")
                    .attr("y", "-16px")
                    .attr("width", "32px")
                    .attr("height", "32px");

                node_s.enter().forEach(function (d) {
                    node_s.append("svg:text")
                        .attr("dy", "1.5em")
                        .attr("class", "node")
                        .attr("text-anchor", "middle")
                        .attr("fill", "#000000")
                        .attr("background", "#c0c0c0")
                        .text(function (d) {
                            return d.name
                        })
                });
                var node = svg.selectAll("g.node");

                node
                    .call(node_drag)
                    .on("mouseover", function(d) { return node_mouseOver(d) })
                    .on("mouseout", function(d) { return node_mouseOut(d) })
                    .on("click", node_onClick)
                ;
                /*node.selectAll("circle").append("title").text(function (d) {
                 return d.name;
                 });*/

                //spinner.stop();


                function tick() {


                    //console.log(node);
                    node.attr("transform", function (d) {
                        return "translate(" + d.x + "," + d.y + ")";
                    });

                    link
                        .attr("x1",function (d) { return d.source.x;})
                        .attr("y1",function (d) { return d.source.y;})
                        .attr("x2",function (d) { return d.target.x;})
                        .attr("y2", function (d) { return d.target.y;}
                    );

                    //node.call( function (d,i) { return node_drag(d,i) });



                }

                var linkedByIndex = {};
                json.links.forEach(function (d) {
                    linkedByIndex[d.source.index + "," + d.target.index] = 1;
                });

                function isConnected(a, b) {
                    return linkedByIndex[a.index + "," + b.index] || linkedByIndex[b.index + "," + a.index] || a.index == b.index;
                }

                function dragstart(d, i) {
                    self.force.stop();
                }

                function dragmove(d, i) {
                    d.px += d3.event.dx;
                    d.py += d3.event.dy;
                    d.x += d3.event.dx;
                    d.y += d3.event.dy;
                    tick();
                }

                function dragend(d, i) {
                    console.log("dragend: " + d.data.sysname);
                    d.fixed = true;
                    tick();
                    self.force.resume();
                }

                function node_mouseOver(d) {
                    mover({'title':d.name, 'description':'', 'css_description_width': 200});
                    fade(d, 0.1);
                }

                function node_mouseOut(d) {
                    mout(d);
                    fade(d, 1);
                }

                function fade(d, opacity) {
                    node.style("stroke-opacity", function (o) {
                        thisOpacity = isConnected(d, o) ? 1 : opacity;
                        this.setAttribute('fill-opacity', thisOpacity);
                        this.setAttribute('opacity', thisOpacity);

                        circle = (this.firstElementChild || this.children[0] || {})

                        text = (this.childNodes[1] || {})

                        v = circle.textContent
                        if (d.name == v) {
                            circle.setAttribute("style", "fill: red");
                            text.setAttribute("style", "fill: red");
                        } else {
                            circle.setAttribute('style', "fill: " + fill(d.group));
                            text.setAttribute('style', "fill: #000");
                        }


                        return thisOpacity;
                    });


                    link.style("stroke-opacity", function (o) {
                        return o.source === d || o.target === d ? 1 : opacity;
                    });

                }

                function link_popup(d) {
                    var inOctets,outOctets,inOctetsRaw,outOctetsRaw = "N/A"

                    if (d.data.traffic['inOctets'] != null) {
                        inOctets = NetmapExtras.convert_bits_to_si(d.data.traffic['inOctets'].raw*8)
                        inOctetsRaw = d.data.traffic['inOctets'].raw
                    } else {
                        inOctets = inOctetsRaw = 'N/A'
                    }
                    if (d.data.traffic['outOctets'] != null) {
                        outOctets = NetmapExtras.convert_bits_to_si(d.data.traffic['outOctets'].raw*8)
                        outOctetsRaw = d.data.traffic['outOctets'].raw
                    } else {
                        outOctets = outOctetsRaw = 'N/A'
                    }

                    mover({
                        'title':'link',
                        'description': d.data.uplink.thiss.interface + " -> " + d.data.uplink.other.interface +
                            '<br />'+ d.data.link_speed +
                            '<br />In: '+ inOctets + " raw["+ inOctetsRaw+"]"+
                            '<br />Out: '+ outOctets + " raw["+ outOctetsRaw+"]"
                        ,
                        'css_description_width': 400
                    });

                }

                function link_popout(d) {
                    mout(d);
                }

                function mover(d) {
                    //console.log('mover!');
                    self.$("#pop-up").fadeOut(100,function () {
                        // Popup content
                        self.$("#pop-up-title").html(d.title);
                        self.$("#pop-img").html("23");
                        self.$("#pop-desc").html(d.description).css({'width':d.css_description_width});

                        // Popup position

                        //console.log(scale);
                        //console.log(trans);

                        var popLeft = (d.x*self.scale)+self.trans[0]-10;//lE.cL[0] + 20;
                        var popTop = (d.y*self.scale)+self.trans[1]+70;//lE.cL[1] + 70;
                        self.$("#pop-up").css({"left":popLeft,"top":popTop});
                        self.$("#pop-up").fadeIn(100);
                    });

                }

                function mout(d) {
                    $("#pop-up").fadeOut(50);
                    //d3.select(this).attr("fill","url(#ten1)");
                }

                function node_onClick(node) {

                    //var netbox_info = new NetboxInfoView({node: node});
                    self.sidebar.node = node;
                    self.sidebar.render();
                    //self.sidebar.html(netbox_info.render().el);
                }

                /*svg.style("opacity", 1e-6)
                 .transition()
                 .duration(10000)
                 .style("opacity", 1);*/

            }

            function categoryFilter(data, selected_categories) {
                var json = data;
                //if (!self.selected_netmap.isNew() && self.selected_netmap.attributes.)

                //var selected_categories = ['other','sw'];

                // can't remove nodes YET, will screw up stupid linksLinkedByIndex!
                // If you don't want to remap links >=index_you_delete by -1 for every
                // delete ...

                var filter_links = [];


                function filterNodes() {
                    var result = [];
                    for (var i = 0; i < json.nodes.length; i++) {
                        var node = json.nodes[i];
                        if (node !== null) {
                            if (node.data.position) {
                                console.log(node);
                                node.x = node.data.position.x;
                                node.y = node.data.position.y;
                                node.fixed = true;
                            }
                            isNodeMatchingFilter = false;
                            for (var k = 0; k < selected_categories.length; k++) {
                                var selected_category = selected_categories[k];
                                if (selected_category.toLowerCase() === node.data.category.toLowerCase()) {
                                    isNodeMatchingFilter = true;
                                    break;
                                    // remove? need to reorder index crap..
                                }
                            }
                            if (isNodeMatchingFilter) {
                                result.push(i);
                            } else if (!node.fixed) {
                                // reset it's coordinates if position is not fixed
                                // and it doesn't match filter.

                                /*node.x = 0;
                                node.y = 0;*/

                            }

                        } else {
                            console.log("THIS IS A BUG");
                            console.log(i);
                        }
                    }
                    return result;
                }

                var filter_nodes_indexes = filterNodes();

                /**
                 * Create new d3_json format:
                 *
                 *
                 * add new node
                 *   add links related to node matching CRITERIA with new index
                 *   run thru already added links & update indexes
                 *
                 *
                 */
                function filterLinks () {
                    var result = [];

                    function isMatchingCriteria () {
                        var sourceMatch = false;
                        var targetMatch = false;
                        var source,target;
                        source = (link.source.index !== undefined ? link.source.index : link.source);
                        target = (link.target.index !== undefined ? link.target.index : link.target);

                        for (var z = 0; z < selected_categories.length; z++) {
                            var selected_category = selected_categories[z].toLowerCase();
                            if (json.nodes[source].data.category.toLowerCase() === selected_category) {
                                sourceMatch = true;
                            }
                            if (json.nodes[target].data.category.toLowerCase() === selected_category) {
                                targetMatch = true;
                            }
                        }
                        return sourceMatch && targetMatch;

                    }

                    console.log(filter_nodes_indexes);
                    for (var x = 0; x < filter_nodes_indexes.length; x++) {
                        var node_index = filter_nodes_indexes[x];
                        for (var i = 0; i < json.links.length; i++) {
                            var link = json.links[i];
                            var source,target;
                            source = (link.source.index !== undefined ? link.source.index : link.source);
                            target = (link.target.index !== undefined ? link.target.index : link.target);

                            if (source === node_index || target === node_index) {
                                if (isMatchingCriteria(link)) {
                                    result.push(link);
                                }
                            }
                        }

                    }
                    return result;
                }
                filter_links = filterLinks();

                return filter_links;
            }


            //var selected_categories = context_selected_map.map.
            //var selected_categories = ['gsw', 'sw'];
            if (self.force !== undefined) {
                self.force.stop();
            }

            var selected_categories = self.context_selected_map.map.attributes.categories;

            this.model.attributes.links = categoryFilter(this.model.toJSON(), selected_categories);
            draw(this.model.toJSON());

            console.log(this.$el);

            return this;
        },
        close:function () {
            $(window).off("resize.app");
            this.$el.unbind();
            this.$el.remove();
        }
    });
    return drawNetmapView;
});





