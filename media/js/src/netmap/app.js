
define([
    'netmap/router', // Request router.js
    'libs/jquery',
    'libs/underscore',
    'libs/backbone'
], function(Router) {
    var initialize = function () {
        self = this;

        // Comment this one out when moving to mod_wsgi! mod_python
        // does not support PUT etc , only GET and POST. Silly mod_python!
        Backbone.emulateHTTP = true;

        //Backbone.emulateJSON = true;
        // Pass in our Router module and call it's initialize function
        Router.initialize();
    };

    return {
        initialize: initialize
    };
});