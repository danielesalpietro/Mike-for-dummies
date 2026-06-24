# Apache Livy — REST API for Apache Spark
# Downloads the official incubating release from Apache mirrors.
FROM eclipse-temurin:11-jre-jammy

ARG LIVY_VERSION=0.8.0-incubating
ARG SPARK_VERSION=3.5.3
ARG HADOOP_VERSION=3

ENV LIVY_HOME=/opt/livy
ENV SPARK_HOME=/opt/spark
ENV PATH="${LIVY_HOME}/bin:${SPARK_HOME}/bin:${PATH}"

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl wget python3 python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install Spark (needed by Livy to submit jobs)
RUN wget -q \
    "https://archive.apache.org/dist/spark/spark-${SPARK_VERSION}/spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}.tgz" \
    -O /tmp/spark.tgz \
    && tar -xzf /tmp/spark.tgz -C /opt/ \
    && mv "/opt/spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}" /opt/spark \
    && rm /tmp/spark.tgz

# Install Livy
RUN wget -q \
    "https://archive.apache.org/dist/incubator/livy/${LIVY_VERSION}/apache-livy-${LIVY_VERSION}_2.12-bin.zip" \
    -O /tmp/livy.zip \
    && apt-get install -y unzip \
    && unzip -q /tmp/livy.zip -d /opt/ \
    && mv "/opt/apache-livy-${LIVY_VERSION}_2.12-bin" /opt/livy \
    && rm /tmp/livy.zip

COPY livy.conf "${LIVY_HOME}/conf/livy.conf"

EXPOSE 8998

CMD ["livy-server", "start"]
