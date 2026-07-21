## Interactive Stories Website

This website makes two contributions to the litany of sofware out there: a basic interactive stories viewer and a website that wraps that viewer. The viewer is simply a modified PDF viewer. 

The viewer is at ``static/pdf-viewer.mjs``. That file is what modifies Mozilla's PDF viewing library to prevent keyboard navigation, keeping your interactive stories _interactive_.

I just import this JS module into the ``templates/view_story.html`` file, a Jinja template that fetches the PDF path of the requested interactive story. 

### To start

#### Requirements:
You need an Azure cloud storage account if you want to store stories on the cloud. Or replace with your own file storage system or use local whatever you want!

* Clone this repo
* Create a Python Virtual Environment and install all packages in the pyproject.toml file. (I use UV for package management, idk its cool)
* Create a `.env` file using `.env.example` as a template.
* Initialize your db
* Create your admin user by running `python scripts/cli.py create-user --admin`
* Start the server by running `python app.py`
* Load the admin page by visiting `localhost:PORT/admin`
* Add your stories in PDF version

### What about PowerPoint?
Convert your PPT interactive stories to PDF easily on PowerPoint and then upload them to the website using the attached SQLite admin panel. To launch the admin panel, visit localhost:PORT/admin.

## Future considerations
* It will be nice for this site to convert PPT to PDFs for you. If you feel like doing that, make a PR!

## Bugs
What bugs ? >.<