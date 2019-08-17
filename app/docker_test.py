import docker
import os
import subprocess
import multiprocessing as mp

work_dir = os.getcwd()
client = docker.from_env()
extractor_names = ['tabular', 'jsonxml', 'netcdf', 'keyword', 'image', 'maps', 'matio']


def build_image(extractor):
    client.images.build(path=os.path.join('dockerfiles', extractor), tag="xtract-" + extractor)


def build_all_images(multiprocess=False):
    for extractor in extractor_names:
        try:
            client.images.remove(image="xtract-" + extractor, force=True)
        except:
            pass
    print("Done deleting")
    if multiprocess == False:
        for extractor in extractor_names:
            client.images.build(path=os.path.join('dockerfiles', extractor), tag="xtract-" + extractor)
    else:
        pools = mp.Pool(processes=mp.cpu_count())
        pools.map(build_image, extractor_names)
        pools.close()
        pools.join()
    print("done building")


# The extractors sometimes return extra things so we have to process it oddly
def extract_metadata(extractor, file_path):
    if extractor in extractor_names:
        try:
            directory = os.path.dirname(file_path)
            file_name = os.path.basename(file_path)

            if extractor == 'tabular':
                os.chdir("dockerfiles/tabular")
                raw_output = subprocess.check_output(["./run.sh", directory, file_name]).decode('utf-8')

                for idx, char in enumerate(reversed(raw_output)):
                    if char == "}":
                        last_char = idx
                        break

                os.chdir(work_dir)
                return raw_output[:len(raw_output) - last_char]

            if extractor == 'jsonxml':
                os.chdir("dockerfiles/jsonxml")
                raw_output = subprocess.check_output(["./run.sh", directory, file_name]).decode('utf-8')

                for idx, char in enumerate(reversed(raw_output)):
                    if char == "}":
                        last_char = idx
                        break

                os.chdir(work_dir)
                return raw_output[:len(raw_output) - last_char]

            if extractor == 'keyword':
                os.chdir("dockerfiles/keyword")
                raw_output = subprocess.check_output(["./run.sh", directory, file_name]).decode('utf-8')

                for idx, char in enumerate(raw_output):
                    if char == "{":
                        last_char = idx
                        break

                os.chdir(work_dir)
                return raw_output[last_char:]

            if extractor == 'maps':
                os.chdir("dockerfiles/maps")
                raw_output = subprocess.check_output(["./run.sh", directory, file_name]).decode('utf-8')

                for idx, char in enumerate(reversed(raw_output)):
                    if char == "}":
                        last_char = idx
                        break

                os.chdir(work_dir)
                return raw_output[:len(raw_output) - last_char]

            if extractor == 'image':
                os.chdir("dockerfiles/image")
                raw_output = subprocess.check_output(["./run.sh", directory, file_name]).decode('utf-8')

                for idx, char in enumerate(raw_output):
                    if char == "{":
                        last_char = idx

                os.chdir(work_dir)
                return raw_output[last_char:]

            if extractor == 'matio':
                os.chdir("dockerfiles/matio")
                raw_output = subprocess.check_output(["./run.sh", directory, file_name]).decode('utf-8')

                os.chdir(work_dir)
                return raw_output

        except Exception as e:
            os.chdir(work_dir)
            return "Failed with exception {}".format(e)
    else:
        return "Not an extractor"



build_all_images(multiprocess=True)
client.images.list()
print("-----------")
print(extract_metadata('matio', "/Users/ryan/Documents/CS/CDAC/official_xtract/xtract-matio/materialsio/tests/data/electron_microscopy/test-1.dm4"))

