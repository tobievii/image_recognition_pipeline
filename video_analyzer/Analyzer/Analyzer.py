#!/usr/bin/env python3

import requests
import analyzer_config as config
import boto3
import datetime as dt
import json
from cassandra.cluster import Cluster
import Cassandra_Connect

class Analyzer():
    
    def __init__(self):
        self.ClientRequestToken = config.analyzer_config["ClientRequestToken"]
        self.JobTag = config.analyzer_config["JobTag"]
        self.MinConfidence = config.analyzer_config["MinConfidence"]
        self.NotificationChannel = config.analyzer_config["NotificationChannel"]["RoleArn"]
        self.SNSTopicArn = config.analyzer_config["NotificationChannel"]["SNSTopicArn"]
        self.SNSRoleArn = config.analyzer_config["NotificationChannel"]["RoleArn"]
        self.Bucket = config.analyzer_config["Video"]["S3Object"]["Bucket"]
        self.Name = config.analyzer_config["Video"]["S3Object"]["Name"]
        self.Video = config.analyzer_config["Video"]



    def test_print(self):
        print(self.ClientRequestToken)
        print(self.JobTag)
        print(self.MinConfidence)
        print(self.NotificationChannel)
        print(self.SNSTopicArn)
        print(self.Bucket)
        print(self.Name)

    def make_request(self):
        data = {
            "ClientRequestToken": self.ClientRequestToken,
            "JobTag": self.JobTag,
            "MinConfidence": self.MinConfidence,
            "NotificationChannel": self.NotificationChannel,
            "SNSTopicArn": self.SNSTopicArn,
            "Bucket": self.Bucket,
            "Name": self.Name
        }

    # def boto_client(self):
        # initialize client
        client = boto3.client('rekognition', region_name='us-west-2')
        
        response = client.start_label_detection(
            Video={
                'S3Object': {
                    'Bucket': self.Bucket,
                    'Name': self.Name
                }
            },
            ClientRequestToken = self.ClientRequestToken,
            MinConfidence = 1.0,
            NotificationChannel = {
                'SNSTopicArn': self.SNSTopicArn,
                'RoleArn': self.SNSRoleArn
            },
            JobTag = self.JobTag
        )
        print(response)       
    
    # Fetch job results and return response
    def get_job_results(self, jobId):
        client = boto3.client('rekognition', region_name='us-west-2')        
        response = client.get_label_detection(
            JobId=jobId,
            MaxResults=100
        )
        # return response for use in next method
        return response
	
    # Build query using reults from 'get_job_results'
    def query_builder(self, jobId):
        self.results = self.get_job_results(jobId)
        self.RequestId = self.results["ResponseMetadata"]["RequestId"] 
        self.ResultsNumber = len(self.results["Labels"])
        truncated_response = [self.results['Labels'][i] for i in range(0, (self.ResultsNumber - 1))]
        label_list = [truncated_response[i]["Label"]["Name"] for i in range(0, (self.ResultsNumber - 1))]
        self.query = "INSERT INTO data_pipeline.rekognition_records (RequestId, Labels) VALUES ('{0}', {1})".format(self.RequestId, label_list)
        return self.query

    # Connect to cluster and execute query that was assembled in previous method
    def execute_query(self, jobId):
        self.query_builder(jobId)
        with Cluster([config.analyzer_config["Cluster"]["Cluster_address"]], port=config.analyzer_config["Cluster"]["Cluster_port"]) as cass_cluster:
            # Connect to nodes on the cluster
            cass_session = cass_cluster.connect('data_pipeline')
            cass_session.execute(self.query)        

analyzer = Analyzer()
#analyzer.make_request()
analyzer.execute_query("78044e5eeb11eb3a6297f2ced44b9ccad7302caba58ede43e3e3230131b2a7a5")
