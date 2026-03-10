import ssl


def get_cert(path: str):
    """
    Get CA certificates

    :param path: location of wincacerts.pem file
    :type: str
    """
    context = ssl.create_default_context()
    der_certs = context.get_ca_certs(binary_form=True)
    pem_certs = [ssl.DER_cert_to_PEM_cert(der) for der in der_certs]

    with open(path, "w") as outfile:
        for pem in pem_certs:
            outfile.write(pem + "\n")
