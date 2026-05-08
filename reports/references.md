# References

All references below were verified live against the CrossRef API
(`https://api.crossref.org/works/{doi}`) at scaffold time. Only entries whose
returned title and authors matched the topic are retained. Format keeps
author / title / journal / year / DOI; volume, issue, and pages are intentionally
omitted to avoid fabrication risk.

## MLOps Core (definitions, surveys, deployment challenges)

1. Kreuzberger D, Kühl N, Hirschl S. Machine Learning Operations (MLOps): Overview, Definition, and Architecture. IEEE Access. 2023. DOI:10.1109/ACCESS.2023.3262138
2. Recupito G, Pecorelli F, Catolino G, et al. A Multivocal Literature Review of MLOps Tools and Features. 48th Euromicro Conference on Software Engineering and Advanced Applications (SEAA). 2022. DOI:10.1109/SEAA56994.2022.00021
3. Paleyes A, Urma R, Lawrence N. Challenges in Deploying Machine Learning: A Survey of Case Studies. ACM Computing Surveys. 2022. DOI:10.1145/3533378
4. Sambasivan N, Kapania S, Highfill H, et al. "Everyone wants to do the model work, not the data work": Data Cascades in High-Stakes AI. CHI Conference on Human Factors in Computing Systems. 2021. DOI:10.1145/3411764.3445518

## ML Pipelines, Serving, and Orchestration

5. Baylor D, Breck E, Cheng H, et al. TFX: A TensorFlow-Based Production-Scale Machine Learning Platform. KDD. 2017. DOI:10.1145/3097983.3098021
6. Caveness E, Polyzotis N, Roy S, et al. TensorFlow Data Validation: Data Analysis and Validation in Continuous ML Pipelines. SIGMOD Conference. 2020. DOI:10.1145/3318464.3384707
7. Chen A, Chow A, Davidson A, et al. Developments in MLflow. DEEM Workshop (SIGMOD companion). 2020. DOI:10.1145/3399579.3399867
8. Burns B, Grant B, Oppenheimer D, et al. Borg, Omega, and Kubernetes. Communications of the ACM. 2016. DOI:10.1145/2890784

## Concept Drift and Data Drift

9. Lu J, Liu A, Dong F, et al. Learning under Concept Drift: A Review. IEEE Transactions on Knowledge and Data Engineering. 2018. DOI:10.1109/TKDE.2018.2876857
10. Gama J, Žliobaitė I, Bifet A, et al. A survey on concept drift adaptation. ACM Computing Surveys. 2014. DOI:10.1145/2523813
11. Bifet A, Gavaldà R. Learning from Time-Changing Data with Adaptive Windowing. SIAM International Conference on Data Mining. 2007. DOI:10.1137/1.9781611972771.42
12. Losing V, Hammer B, Wersing H. Incremental on-line learning: A review and comparison of state of the art algorithms. Neurocomputing. 2018. DOI:10.1016/j.neucom.2017.06.084

## Continuous Delivery, DevOps, and Microservices

13. Chen L. Continuous Delivery: Huge Benefits, but Challenges Too. IEEE Software. 2015. DOI:10.1109/MS.2015.27
14. Jamshidi P, Pahl C, Mendonca N, et al. Microservices: The Journey So Far and Challenges Ahead. IEEE Software. 2018. DOI:10.1109/MS.2018.2141039

## Industrial Anomaly Detection (federated module #7)

15. Bergmann P, Fauser M, Sattlegger D, et al. MVTec AD: A Comprehensive Real-World Dataset for Unsupervised Anomaly Detection. CVPR. 2019. DOI:10.1109/CVPR.2019.00982
16. Pang G, Shen C, Cao L, et al. Deep Learning for Anomaly Detection: A Review. ACM Computing Surveys. 2021. DOI:10.1145/3439950
17. Defard T, Setkov A, Loesch A, et al. PaDiM: A Patch Distribution Modeling Framework for Anomaly Detection and Localization. ICPR Workshops. 2021. DOI:10.1007/978-3-030-68799-1_35
18. Gudovskiy D, Ishizaka S, Kozuka K. CFLOW-AD: Real-Time Unsupervised Anomaly Detection with Localization via Conditional Normalizing Flows. WACV. 2022. DOI:10.1109/WACV51458.2022.00188
19. Lindemann B, Maschler B, Sahlab N, et al. A survey on anomaly detection for technical systems using LSTM networks. Computers in Industry. 2021. DOI:10.1016/j.compind.2021.103498

## Foundational ML Methods (used across all three federated modules)

20. Breiman L. Random Forests. Machine Learning. 2001. DOI:10.1023/A:1010933404324
21. Friedman J. Greedy function approximation: A gradient boosting machine. Annals of Statistics. 2001. DOI:10.1214/aos/1013203451
22. Chen T, Guestrin C. XGBoost: A Scalable Tree Boosting System. KDD. 2016. DOI:10.1145/2939672.2939785
23. LeCun Y, Boser B, Denker J, et al. Backpropagation Applied to Handwritten Zip Code Recognition. Neural Computation. 1989. DOI:10.1162/neco.1989.1.4.541
24. He H, Garcia E. Learning from Imbalanced Data. IEEE Transactions on Knowledge and Data Engineering. 2009. DOI:10.1109/TKDE.2008.239
25. Sokolova M, Lapalme G. A systematic analysis of performance measures for classification tasks. Information Processing and Management. 2009. DOI:10.1016/j.ipm.2009.03.002

## Federated Learning and Multi-Tenant ML

26. Yang Q, Liu Y, Chen T, et al. Federated Machine Learning: Concept and Applications. ACM Transactions on Intelligent Systems and Technology. 2019. DOI:10.1145/3298981

## Industry 4.0 and Smart Manufacturing (DACH context for capstone)

27. Leng J, Wang D, Shen W, et al. Digital twins-based smart manufacturing system design in Industry 4.0. Journal of Manufacturing Systems. 2021. DOI:10.1016/j.jmsy.2021.05.011

---

**Verification method.** Each DOI above was queried with
`GET https://api.crossref.org/works/{doi}` during scaffold. Entries returning
4xx or whose returned title did not match the cited topic were dropped. No
volume, issue, or page numbers are listed because CrossRef pagination metadata
varies in completeness; the DOI is the canonical identifier and resolves
deterministically.
