# Intelligent Restaurant Management System (IRMS)

## Objective:

The purpose of this assignment is to design a software architecture and implement an Intelligent Restaurant Management System (IRMS) that leverages IoT devices to streamline customer ordering processes and optimize kitchen operations. The system aims to automate order placement, synchronize order flow between dining areas and the kitchen, and enhance order queue management. The goal is to create a solution that uses IoT technologies to improve service quality, reduce delays, and ensure consistent kitchen performance.

## Context:

An Intelligent Restaurant Management System (IRMS) incorporating IoT devices is a modern software application designed to improve restaurant efficiency by automating key operational tasks. IoT-enabled tables, menus, and sensors allow customers to place orders directly through smart tablets, or QR menus, transmitting order data instantly to the kitchen.

The IRMS continuously collects data from these IoT devices to coordinate kitchen workflows, manage order queues, and prevent errors. The system adapts dynamically to order volume, equipment availability, and cooking status. It ensures that orders are processed in the correct order, cooking times align with expected service times, and staff are notified of any issues requiring intervention.

The system also provides managers and staff with dashboards displaying real-time kitchen activities, device statuses, inventory levels, and order progress, allowing proactive decision making and efficient restaurant operations.

## Scope of the System:

* IoT-Based Ordering System
  * Smart menus on IoT-enabled tablets, or QR menus allow customers to place orders without waiting for staff.
  * Orders are automatically validated, categorized (e.g., drink, appetizer, main dish), and sent to relevant kitchen stations.
* Real-Time Order Queue Management
  * Orders are displayed on IoT-connected kitchen display systems (KDS) that dynamically update based on cooking progress and station load.
  * Smart prioritization automatically reorders the queue based on dish complexity, kitchen’s capacity, and service time commitments.
  * Staff receive alerts when certain dishes require attention or when a station becomes overloaded.
* Inventory & Ingredient Tracking
  * Load-cell sensors in ingredient bins track real-time ingredient usage and notify the manager when supplies run low.
  * Refrigerator and freezer sensors monitor temperature to maintain food safety.
* Staff & Manager Dashboards
  * Real-time dashboards display order status, kitchen load, and alerts.
  * Managers may review analytics on order flow, table turnover, and payment status.
  * Predictive insights help with scheduling staff, optimizing menus, and forecasting busy periods

## Assignment Tasks:

### Task 1: Software Architecture Design

1. Thoroughly describe the context of the Intelligent Tutoring System (IRMS) based on the basic information provided. This includes clearly identifying functional and nonfunctional requirements, outlining the objectives and scope of the project, etc.
2. Create the software architecture for the IRMS: The software architecture should include:
* Architecture Characteristics define the success criteria of the IRMS.
* Structure:
  * Compare and choose suitable architecture styles to apply to the IRMS.
  * Present the software architecture in different views including module views, component–and–connector views, and allocation views.
* Architecture Decisions define the rules for how the IRMS should be constructed.
* Design Principles: Guidelines for constructing the IRMS.
3. Apply SOLID Principles: explain how the SOLID principles have been applied in your design
4. Reflection Report: Write a brief reflection on how applying SOLID principles helped you improve the design of the IRMS. Discuss challenges you faced and how adhering to these principles made your system more modular, maintainable, and extensible.

### Task 2: Code Implementation (choose at least one main module to implement)
1. Implement Core Functionalities: Implement key system features based on your design, ensuring the code adheres to the SOLID principles. 