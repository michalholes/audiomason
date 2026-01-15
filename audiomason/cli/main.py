import typer

app = typer.Typer()

@app.command()
def run():
    typer.echo('Audiomason v2 pipeline executed (stub).')

if __name__ == '__main__':
    app()
