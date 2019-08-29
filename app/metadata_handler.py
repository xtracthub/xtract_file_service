from app import celery_app, db
from celery.exceptions import SoftTimeLimitExceeded
from app.models import User, FileMetadata
from app.docker_handler import extract_metadata
import os
import ast


@celery_app.task(bind=True, default_retry_delay=0)
def extract_user_metadata(self, file_path, authentication, extractor, cli_args=[]):
    """Extracts metadata from a file and writes a FileMetadata objeect to the SQL server.

    Parameters:
    file_path (str): File path of file to extract metadata from.
    authentication (str): User authentication as returned by login().
    extractor (str): Name of extractor to use to extract metadata.
    cli_args (str): Additional command line arguments to pass to the extractors.
    """
    try:
        metadata_str = extract_metadata(extractor, file_path, cli_args)
        user = User.query.filter_by(user_uuid=authentication).first()
        file_metadata = FileMetadata(file_path=file_path, metadata_dict=metadata_str, user=user, extractor=extractor)
        db.session.add(file_metadata)
        db.session.commit()
        try:
            metadata_dict = ast.literal_eval(metadata_str)
            if "json/xml" == list(metadata_dict.keys())[0]:
                for metadata in FileMetadata.query.filter_by(file_path=file_path, user_uuid=authentication,
                                                             extractor='keyword'):
                    db.session.delete(metadata)
                db.session.commit()
                extract_user_metadata.apply_async(args=[file_path, authentication, "keyword",
                                                        ["--text_string", metadata_dict["json/xml"]["strings"]]],
                                                  time_limit=10, queue='priority')
            elif "tabular" == list(metadata_dict.keys())[0]:
                for metadata in FileMetadata.query.filter_by(file_path=file_path, user_uuid=authentication,
                                                             extractor='keyword'):
                    db.session.delete(metadata)
                db.session.commit()
                extract_user_metadata.apply_async(args=[file_path, authentication, "keyword",
                                                  ["--text_string", ' '.join(metadata_dict["tabular"]["physical"]["preamble"])]],
                                                  time_limit=10, queue='priority')
        except:
            pass

    except SoftTimeLimitExceeded:
        self.retry(soft_time_limit=None)

    return metadata_str


def delete_user_metadata(file_path, authentication):
    """Deletes a users metadata for a given file.

    Parameters:
    file_path (str): File path of metadata to delete.
    authentication (str): User authentication as returned by login().
    """
    metadata_to_delete = FileMetadata.query.filter_by(file_path=file_path, user_uuid=authentication).all()

    if len(metadata_to_delete) == 0:
        return "Metadata for {} does not exist\n".format(os.path.basename(file_path))
    else:
        for metadata in metadata_to_delete:
            db.session.delete(metadata)
        db.session.commit()

        return "Successfully deleted metadata for {}\n".format(os.path.basename(file_path))