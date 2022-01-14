This program provides a searchable interface to your ASL magazines and their articles.

<a href="https://github.com/pacman-ghost/asl-articles/raw/master/doc/publishers.png" target="_blank">
<img src="https://github.com/pacman-ghost/asl-articles/raw/master/doc/publishers.png" height="150">
</a>
&nbsp;
<a href="https://github.com/pacman-ghost/asl-articles/raw/master/doc/publication.png" target="_blank">
<img src="https://github.com/pacman-ghost/asl-articles/raw/master/doc/publication.png" height="150">
</a>
&nbsp;
<a href="https://github.com/pacman-ghost/asl-articles/raw/master/doc/search.png" target="_blank">
<img src="https://github.com/pacman-ghost/asl-articles/raw/master/doc/search.png" height="150">
</a>
&nbsp;
<a href="https://github.com/pacman-ghost/asl-articles/raw/master/doc/tag.png" target="_blank">
<img src="https://github.com/pacman-ghost/asl-articles/raw/master/doc/tag.png" height="150">
</a>

*NOTE: This project integrates with my other [asl-rulebook2](https://github.com/pacman-ghost/asl-rulebook2) project. Add a setting to your `site.cfg` e.g.*

``` ASLRB_BASE_URL = http://localhost:5020 ```

*and references to rules will be converted to clickable links that will open the ASLRB at that rule.*

### To run the application

Get a copy of the pre-loaded database from the release page.

Then go to the project root directory and run the following command:

```
    ./run-containers.sh -d /home/pacman-ghost/asl-articles.db
```

*NOTE: You will need Docker >= 17.05 (for multi-stage builds)*, and `docker-compose`.

Then open a browser and go to http://localhost:3002

When you add content to your database, it is recommended (although not essential) that for each publisher, you add their publications in chronological order i.e. the oldest ones first.

### To link publications and articles to their source documents

It is possible to configure publications and their articles so that clicking them will open the original source document. These will typically be PDF's, and if you have fast, always-on internet, you could link to them using a *http://* URL. However, if you've downloaded them to your computer and want to link to them there, things are a bit more complicated.

For security reasons, browsers don't allow *file://* links to PDF's, they must be served by a web server. This program supports this, but some things need to be set up first.

When you run the application, specify the top-level directory that contains your PDF's in the command line e.g.

```
    ./run-containers.sh \
        -d /home/pacman-ghost/asl-articles.db \
        -e /home/pacman-ghost/asl-articles-docs/
```

Then, configure your document paths *relative to that directory*.

For example, say I have my files organized like this:

```
* /home/pacman-ghost/
+-- asl-articles.db
+-- asl-articles-docs/
    +-- vftt/
        +-- vftt01.pdf
        +-- vftt02.pdf
        +-- etc...
```

I would specify the document directory when I launch the application (as above). Then, for the publication *View From The Trenches #1*, I would configure its URL as *vftt/vftt01.pdf* i.e. the path to the document *relative to the document base directory*.

*NOTE: You don't need to configure a URL for each individual article, just set it once for the parent publication and each article will default to that. If you specify the page number for an article, it will even open at the correct page!*

### For developers

The application is split over 2 Docker containers, one running a React front-end, the other running a Flask back-end.

##### Setting up the Flask (Python) back-end

Create a *virtualenv*, then go to the *asl_articles/* directory and install the requirements:

```pip install -e .[dev]```

Copy *config/site.cfg.example* to *config/site.cfg*, and update it to point to your database.

Then run the server:

```./run-server.py```

You can test if things are working by opening a browser and going to http://localhost:5000/ping

*NOTE: You can run the test suite using pytest, but the React front-end must be running (see below).*

##### Setting up the React front-end

Go to the *web/* directory and install the requirements:

```npm install```

Then run the server:

```npm start```
