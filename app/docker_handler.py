import docker
import os
import subprocess
import multiprocessing as mp

work_dir = os.getcwd()
client = docker.from_env()
extractor_names = ['tabular', 'jsonxml', 'netcdf', 'keyword', 'image', 'maps', 'matio']


def build_image(extractor):
    """Helper function for building multiple images using multiprocessing.

    Parameter:
    extractor (str): Name of the extractor image to build (one of the items from the extractor_names list).
    """
    client.images.build(path=os.path.join('dockerfiles', extractor), tag="xtract-" + extractor)


def build_all_images(multiprocess=False):
    """Builds all extractor images from the extractor_names list.

    Parameter:
    multiprocess (bool): Whether to build the images in parallel or not. Currently works when used as a standalone
    function but does not work when implemented in the apps/__init__.py file.
    """
    for extractor in extractor_names:
        try:
            client.images.remove(image="xtract-" + extractor, force=True)
        except:
            pass
    print("Done deleting")
    if multiprocess is False:
        for extractor in extractor_names:
            print(os.path.join('app/dockerfiles', extractor))
            client.images.build(path=os.path.join('app/dockerfiles', extractor), tag="xtract-" + extractor)
    else:
        pools = mp.Pool(processes=mp.cpu_count())
        pools.map(build_image, extractor_names)
        pools.close()
        pools.join()
    print("Done building")


# The extractors sometimes return extra things such as extraction time so we have to process it oddly
def extract_metadata(extractor, file_path):
    """Extracts metadata from a file using only a single extractor.

    extractor (str): Extractor name from extractor_names list.
    file_path (str): File path of file to extract metadata from.

    Returns:
    (dict): Dictionary containing metadata.
    """
    if extractor in extractor_names:
        directory = os.path.abspath(os.path.dirname(file_path))
        file_name = os.path.basename(file_path)
        
        try:
            if extractor in ['tabular', 'jsonxml', 'maps', 'netcdf']:
                os.chdir("app/dockerfiles/{}".format(extractor))
                raw_output = subprocess.check_output(["./run.sh", directory, file_name]).decode('utf-8')

                for idx, char in enumerate(reversed(raw_output)):
                    if char == "}":
                        last_char = idx
                        break

                os.chdir(work_dir)
                return raw_output[:len(raw_output) - last_char]

            elif extractor in ['keyword', 'image', 'matio']:
                os.chdir("app/dockerfiles/{}".format(extractor))
                raw_output = subprocess.check_output(["./run.sh", directory, file_name]).decode('utf-8')

                for idx, char in enumerate(raw_output):
                    if char == "{":
                        last_char = idx
                        break

                os.chdir(work_dir)
                return raw_output[last_char:]

        except:
            os.chdir(work_dir)
            return "The {} extractor failed to extract metadata from {}".format(extractor, file_name)
    else:
        return "Not an extractor"

