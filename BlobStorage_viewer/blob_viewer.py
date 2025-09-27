from azure.storage.blob import BlobServiceClient
import sys

# Remplacez par votre URL de compte de stockage + SAS token
# Exemple : "[https://%3caccount_name%3e.blob.core.windows.net/?%3csas_token%3e]https://<account_name>.blob.core.windows.net/?<sas_token>"
sas_url = "[https://%3caccount_name%3e.blob.core.windows.net/?%3csas_token%3e]https://<account_name>.blob.core.windows.net/?<sas_token>"
def list_containers_and_blobs(sas_url: str):
    try:
        # Connexion avec l'URL SAS
        blob_service_client = BlobServiceClient(account_url=sas_url)
        # Lister les containers
        print("== Containers ==")
        containers = blob_service_client.list_containers()
        for container in containers:
            print(f"\n📦 Container : {container['name']}")
            container_client = blob_service_client.get_container_client(container['name'])
            # Lister les blobs (fichiers) dans chaque container
            blobs = container_client.list_blobs()
            for blob in blobs:
                print(f"   └── {blob.name}")

    except Exception as e:
        print(f"Erreur : {e}")
        sys.exit(1)

if __name__ == "__main__":
    list_containers_and_blobs(sas_url)