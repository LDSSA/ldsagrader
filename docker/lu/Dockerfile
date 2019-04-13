FROM conda/miniconda3

ARG LOCAL_LU_PATH=.lu
ARG CONTAINER_LU_PATH=/opt/lu
ARG PACKAGE=ldsagrader-0.1.0.tar.gz

EXPOSE 8888
SHELL ["/bin/bash", "-c"]

# Update conda
RUN conda update conda

# TODO should use the students version
# TODO instructors validation of notebook
# Copy learning unit and create environment
COPY ${LOCAL_LU_PATH} ${CONTAINER_LU_PATH}
RUN cd /opt/lu && conda env create -n LU -f environment.yml

# Copy run script
COPY docker/lu/run.sh /opt/run.sh

# Copy & install grading code
COPY dist/${PACKAGE} /tmp/
RUN source /usr/local/bin/activate LU && \
    cd /tmp && \
    pip --no-cache-dir install ${PACKAGE}
RUN rm -rf /tmp/${PACKAGE}

WORKDIR ${CONTAINER_LU_PATH}
