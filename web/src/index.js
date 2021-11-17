import React from "react" ;
import ReactDOM from "react-dom" ;
import { BrowserRouter, Route, Switch } from "react-router-dom" ;
import { App, gAppRef } from "./App" ;
import { PublicationSearchResult } from "./PublicationSearchResult" ;
import "./index.css" ;

const axios = require( "axios" ) ;

// --------------------------------------------------------------------

ReactDOM.render(
    <BrowserRouter>
        <Switch>
            <Route path="/publishers" render={ (props) => <App {...props} type="publishers" key="publishers"
                doSearch = { () => gAppRef._showPublishers() }
            /> } />
            <Route path="/technique" render={ (props) => <App {...props} type="technique" key="technique"
                doSearch = { () => gAppRef._showTechniqueArticles() }
            /> } />
            <Route path="/tips" render={ (props) => <App {...props} type="tips" key="tips"
                doSearch = { () => gAppRef._showTipsArticles() }
            /> } />
            <Route path="/publisher/:publId" render={ (props) => <App {...props} type="publisher" key={"publ:"+props.match.params.publId}
                doSearch = { () => gAppRef.runSpecialSearch( "/search/publisher/"+gAppRef.props.match.params.publId, null,
                    () => gAppRef.setWindowTitleFromSearchResults( "publisher", "publ_id", gAppRef.props.match.params.publId, "publ_name" )
                ) }
            /> } />
            <Route path="/publication/:pubId" render={ (props) => <App {...props} type="publication" key={"pub:"+props.match.params.pubId}
                doSearch = { () => gAppRef.runSpecialSearch( "/search/publication/"+gAppRef.props.match.params.pubId, null,
                    () => gAppRef.setWindowTitleFromSearchResults( "publication", "pub_id", gAppRef.props.match.params.pubId,
                        sr => { return PublicationSearchResult.makeDisplayName( sr ) }
                ) ) }
            /> } />
            <Route path="/article/:articleId" render={ (props) => <App {...props} type="article" key={"article:"+props.match.params.articleId}
                doSearch = { () => gAppRef.runSpecialSearch( "/search/article/"+gAppRef.props.match.params.articleId, null,
                    () => gAppRef.setWindowTitleFromSearchResults( "article", "article_id", gAppRef.props.match.params.articleId, "article_title" )
                ) }
            /> } />
            <Route path="/author/:authorId" render={ (props) => <App {...props} type="author" key={"author:"+props.match.params.authorId}
                doSearch = { () => gAppRef.runSpecialSearch( "/search/author/"+gAppRef.props.match.params.authorId, null,
                    () => {
                        axios.get(
                            gAppRef.makeFlaskUrl( "/author/" + gAppRef.props.match.params.authorId )
                        ).then( resp => {
                            const author = resp.data ;
                            gAppRef.setWindowTitle( author ? author.author_name : "Unknown author" )
                        } ) ;
                    }
                ) }
            /> } />
            <Route path="/tag/:tag" render={ (props) => <App {...props} type="tag" key={"tag:"+props.match.params.tag}
                doSearch = { () => gAppRef.runSpecialSearch( "/search/tag/"+gAppRef.props.match.params.tag, null,
                    () => gAppRef.setWindowTitle( gAppRef.props.match.params.tag )
                ) }
            /> } />
            <Route path="/" exact component={App} />
            <Route path="/" render={ (props) => <App {...props} warning="Unknown URL." type="home" key="unknown-url" /> } />
        </Switch>
    </BrowserRouter>,
    document.getElementById( "app" )
) ;
