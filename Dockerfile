FROM condaforge/mambaforge:24.3.0-0

ENV DEBIAN_FRONTEND=noninteractive TZ=Asia/Tokyo

RUN apt-get update && apt-get install -y --no-install-recommends \
    tini git curl ca-certificates vim nano less unzip && \
    rm -rf /var/lib/apt/lists/*
    

RUN mamba install -y -c conda-forge \
    python \
    isce2 \
    mintpy \
    snaphu \
    gdal proj \
    numpy=1.26.* \
    scipy \
    h5py \
    cython \
    pandas \
    xarray \
    dask \
    matplotlib \
    ipykernel \
    ipywidgets \
    jupyterlab \
    geopandas \
    asf_search \
 && mamba clean -afy \
 && pip install --no-cache-dir data_downloader==1.2



ARG USERNAME=gray
ARG UID=1000
ARG GID=1000
RUN groupadd -g ${GID} ${USERNAME} && \
    useradd -m -s /bin/bash -u ${UID} -g ${GID} ${USERNAME}

ARG ISCE2_REF=main
RUN git clone --depth=1 --branch ${ISCE2_REF} https://github.com/isce-framework/isce2.git /opt/isce2 \
 && chown -R ${USERNAME}:${USERNAME} /opt/isce2

USER ${USERNAME}
WORKDIR /work

CMD ["/bin/bash"]