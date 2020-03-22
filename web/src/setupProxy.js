const proxy = require( "http-proxy-middleware" ) ;

module.exports = function( app ) {
    // proxy all "/api/..." requests to the Flask backend server
    // NOTE: This only applies in the dev environment, production requires nginx proxying to be configured.
    app.use( "/api", proxy( {
        target: process.env.REACT_APP_FLASK_URL,
        pathRewrite: { "^/api/": "/" },
        changeOrigin: true,
    } ) ) ;
    app.use( "/user", proxy( {
        target: process.env.REACT_APP_FLASK_URL,
        pathRewrite: { "^/user/": "/user-files/" },
        changeOrigin: true,
    } ) ) ;
}
